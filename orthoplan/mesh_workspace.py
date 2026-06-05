from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.io.stl_import import inspect_stl
from orthoplan.model.assets import MeshAsset, MeshProvenance

REGISTRY_FILENAME = "mesh_registry.json"


class MeshRegistryEntry(BaseModel):
    mesh_asset_id: str
    filename: str
    original_reference: str | None = None
    sha256: str | None = None


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
    root.mkdir(parents=True, exist_ok=True)
    (root / REGISTRY_FILENAME).write_text(registry.model_dump_json(indent=2), encoding="utf-8")


def register_stl_mesh(
    stl_path: str | Path,
    *,
    workspace: str | Path | None = None,
    provenance: MeshProvenance = MeshProvenance.IMPORTED,
) -> MeshAsset:
    """Copy an STL into the local mesh workspace and register it by asset id."""

    source = Path(stl_path)
    asset = inspect_stl(source, provenance=provenance)
    root = Path(workspace) if workspace else default_mesh_workspace()
    mesh_dir = root / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{asset.id}.stl"
    shutil.copy2(source, mesh_dir / filename)

    registry = read_registry(root)
    registry.entries[asset.id] = MeshRegistryEntry(
        mesh_asset_id=asset.id,
        filename=f"meshes/{filename}",
        original_reference=asset.reference,
        sha256=asset.sha256,
    )
    write_registry(registry, root)
    return asset


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
