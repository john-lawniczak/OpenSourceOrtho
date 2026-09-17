from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.io.atomic import atomic_write_text
from orthoplan.io.mesh_import import ScanImport, read_scan
from orthoplan.io.stl_export import canonical_bytes, canonical_suffix
from orthoplan.model.assets import MeshAsset, MeshProvenance

REGISTRY_FILENAME = "mesh_registry.json"


class MeshRegistryEntry(BaseModel):
    mesh_asset_id: str
    filename: str
    original_reference: str | None = None
    sha256: str | None = None
    # What the user actually uploaded, before canonicalization (e.g. "ply-le",
    # "glb", "fbx-binary"). ``filename`` always points at the canonical copy.
    source_format: str | None = None
    geometry_kind: str = "mesh"


class MeshRegistry(BaseModel):
    entries: dict[str, MeshRegistryEntry] = Field(default_factory=dict)


def default_mesh_workspace() -> Path:
    return Path.cwd() / ".orthoplan-meshes"


def read_registry(workspace: str | Path | None = None) -> MeshRegistry:
    root = Path(workspace) if workspace else default_mesh_workspace()
    path = root / REGISTRY_FILENAME
    if not path.exists():
        return MeshRegistry()
    return MeshRegistry.model_validate_json(path.read_text(encoding="utf-8"))


def write_registry(registry: MeshRegistry, workspace: str | Path | None = None) -> None:
    root = Path(workspace) if workspace else default_mesh_workspace()
    atomic_write_text(root / REGISTRY_FILENAME, registry.model_dump_json(indent=2))


def register_scan_mesh(
    scan_path: str | Path,
    *,
    workspace: str | Path | None = None,
    provenance: MeshProvenance = MeshProvenance.IMPORTED,
) -> MeshAsset:
    """Import a scan in any supported format and register it by asset id.

    The file is parsed once, stored in the workspace's canonical form (binary
    STL for a mesh, XYZ for a point cloud), and indexed under the hash of the
    ORIGINAL bytes - so re-importing the same export always resolves to the
    same asset regardless of how it is stored here.
    """

    source = Path(scan_path)
    scan = read_scan(source, provenance=provenance)
    root = Path(workspace) if workspace else default_mesh_workspace()
    mesh_dir = root / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    filename = _write_canonical(source, scan, mesh_dir)

    registry = read_registry(root)
    registry.entries[scan.asset.id] = MeshRegistryEntry(
        mesh_asset_id=scan.asset.id,
        filename=f"meshes/{filename}",
        original_reference=scan.asset.reference,
        sha256=scan.asset.sha256,
        source_format=scan.asset.format,
        geometry_kind=scan.asset.geometry_kind,
    )
    write_registry(registry, root)
    return scan.asset


#: Retained name for callers that predate multi-format intake.
register_stl_mesh = register_scan_mesh


def _write_canonical(source: Path, scan: ScanImport, mesh_dir: Path) -> str:
    """Store the canonical copy, passing STL through byte-for-byte."""

    suffix = canonical_suffix(scan.payload)
    filename = f"{scan.asset.id}{suffix}"
    if scan.asset.format.startswith("stl-"):
        shutil.copy2(source, mesh_dir / filename)
    else:
        (mesh_dir / filename).write_bytes(canonical_bytes(scan.payload))
    return filename


def resolve_mesh_path(mesh_asset_id: str, *, workspace: str | Path | None = None) -> Path | None:
    """Resolve a registered mesh id to a file under the workspace, or None."""

    if not _safe_asset_id(mesh_asset_id):
        return None
    root = (Path(workspace) if workspace else default_mesh_workspace()).resolve()
    registry = read_registry(root)
    entry = registry.entries.get(mesh_asset_id)
    if not entry:
        return None
    candidate = (root / entry.filename).resolve()
    if not candidate.is_file() or not candidate.is_relative_to(root):
        return None
    return candidate


def _safe_asset_id(value: str) -> bool:
    return bool(value) and all(char.isalnum() or char in {"-", "_"} for char in value)
