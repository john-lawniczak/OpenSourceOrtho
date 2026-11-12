from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from orthoplan.io.mesh_import import MAX_SCAN_BYTES
from orthoplan.io.mesh_formats import parse_bytes
from orthoplan.mesh_workspace import resolve_mesh_path
from orthoplan.model.geometry import Vec3
from orthoplan.model.plan import SegmentedToothMesh, TreatmentPlan


Triangle = tuple[Vec3, Vec3, Vec3]


def reviewed_triangles_by_tooth(
    plan: TreatmentPlan,
    *,
    workspace: str | Path | None = None,
) -> dict[str, list[Triangle]]:
    """Load full STL triangles for reviewed tooth fragments in the workspace."""

    triangles: dict[str, list[Triangle]] = {}
    for link in plan.tooth_meshes:
        loaded = reviewed_fragment_triangles(link, workspace=workspace)
        if loaded:
            triangles[link.tooth.value] = loaded
    return triangles


def reviewed_fragment_triangles(
    link: SegmentedToothMesh,
    *,
    workspace: str | Path | None = None,
) -> list[Triangle] | None:
    """Real triangles for a reviewed segmentation link, or None to fail closed."""

    if not link.reviewed:
        return None
    path = resolve_mesh_path(link.mesh_asset_id, workspace=workspace)
    if path is None:
        return None
    try:
        stat = path.stat()
        if stat.st_size > MAX_SCAN_BYTES:
            return None
        return _fragment_triangles(str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=32)
def _fragment_triangles(path: str, modified_ns: int, size: int) -> list[Triangle] | None:
    # Geometry is immutable and keyed by file identity. Quality metadata already
    # lives in the plan; re-running metadata inspection is unnecessary here.
    source = Path(path)
    payload = parse_bytes(source.read_bytes(), suffix=source.suffix, path=source)
    return payload.triangles() if payload.faces else None
