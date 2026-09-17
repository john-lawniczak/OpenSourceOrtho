"""Write per-tooth segment triangles to binary STL and register them locally.

Each :class:`~orthoplan.segmentation.heuristic.ToothSegment` becomes a binary STL
under the local mesh workspace (provenance ``model-generated``), so it is served
by ``GET /api/mesh/<id>`` exactly like any other registered tooth mesh. Nothing
leaves the machine; this is the on-device path.
"""

from __future__ import annotations

import os
import tempfile

from orthoplan.io.stl_export import binary_stl_bytes
from orthoplan.mesh_workspace import register_scan_mesh
from orthoplan.model.assets import MeshAsset, MeshProvenance
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import Triangle, ToothSegment

__all__ = [
    "binary_stl_bytes",
    "export_proposal_rows",
    "surface_sample_points",
    "write_segment_meshes",
]


def write_segment_meshes(
    segments: list[ToothSegment],
    *,
    workspace: str | os.PathLike[str] | None = None,
) -> list[tuple[ToothSegment, MeshAsset]]:
    """Write + register one binary STL per segment; return (segment, asset) pairs."""

    results: list[tuple[ToothSegment, MeshAsset]] = []
    for segment in segments:
        data = binary_stl_bytes(segment.triangles)
        tmp = tempfile.NamedTemporaryFile(suffix=".stl", delete=False)
        try:
            tmp.write(data)
            tmp.close()
            asset = register_scan_mesh(
                tmp.name,
                workspace=workspace,
                provenance=MeshProvenance.MODEL_GENERATED,
            )
        finally:
            os.unlink(tmp.name)
        results.append((segment, asset))
    return results


def surface_sample_points(triangles: list[Triangle], *, limit: int = 64) -> list[Vec3]:
    """Representative, deterministic tooth-surface samples for pure plan rules."""

    unique: list[Vec3] = []
    seen: set[Vec3] = set()
    for tri in triangles:
        for vertex in tri:
            point = tuple(round(component, 6) for component in vertex)  # type: ignore[assignment]
            if point not in seen:
                seen.add(point)
                unique.append(point)
    if len(unique) <= limit:
        return unique
    last = len(unique) - 1
    indexes = {round(i * last / (limit - 1)) for i in range(limit)}
    return [unique[i] for i in sorted(indexes)]


def export_proposal_rows(
    segments: list[ToothSegment],
    *,
    arch: str,
    workspace: str | os.PathLike[str] | None = None,
):
    """Write segments and build the proposal rows + plan-fragment links.

    Returns ``(proposed, assets, links)`` - the reviewable per-tooth rows for the
    /api/segment response, the registered mesh assets, and the ready-to-merge
    ``SegmentedToothMesh`` links (still drafts: ``reviewed`` stays False).
    """

    from orthoplan.model.plan import SegmentedToothMesh, ToothId
    from orthoplan.planning.mesh_frame import compute_local_frame
    from orthoplan.segmentation.auto import ProposedTooth

    proposed: list[ProposedTooth] = []
    assets: list[MeshAsset] = []
    links: list[SegmentedToothMesh] = []
    for segment, mesh_asset in write_segment_meshes(segments, workspace=workspace):
        assets.append(mesh_asset)
        flat = [v for tri in segment.triangles for v in tri]
        links.append(
            SegmentedToothMesh(
                tooth=ToothId(value=segment.tooth_value),
                mesh_asset_id=mesh_asset.id,
                source=MeshProvenance.MODEL_GENERATED,
                local_frame=compute_local_frame(flat),
                surface_sample_points=surface_sample_points(segment.triangles),
                notes=f"auto-segment draft (confidence {segment.confidence:.2f})",
            )
        )
        proposed.append(
            ProposedTooth(
                arch=arch,
                tooth=segment.tooth_value,
                confidence=segment.confidence,
                mesh_asset_id=mesh_asset.id,
                url=f"/api/mesh/{mesh_asset.id}",
                centroid=segment.centroid,
                vertex_count=segment.vertex_count,
            )
        )
    return proposed, assets, links
