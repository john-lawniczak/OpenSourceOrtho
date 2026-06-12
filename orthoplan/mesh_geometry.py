from __future__ import annotations

from pathlib import Path

from orthoplan.io.stl_import import read_stl_geometry
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
        _asset, vertices = read_stl_geometry(path)
    except (OSError, ValueError):
        return None
    triangles: list[Triangle] = []
    for index in range(0, len(vertices) - 2, 3):
        triangles.append((vertices[index], vertices[index + 1], vertices[index + 2]))
    return triangles or None
