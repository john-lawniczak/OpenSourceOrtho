from __future__ import annotations

from orthoplan.model import MeshAsset, MeshProvenance, SegmentedToothMesh, ToothId
from orthoplan.model.geometry import ToothLocalFrame


def link_tooth_mesh(
    *,
    tooth: ToothId,
    mesh_asset: MeshAsset,
    source: MeshProvenance = MeshProvenance.MANUAL,
    local_frame: ToothLocalFrame | None = None,
    notes: str | None = None,
) -> SegmentedToothMesh:
    """Create an explicit tooth-to-mesh link for manual/imported segmentation."""

    return SegmentedToothMesh(
        tooth=tooth,
        mesh_asset_id=mesh_asset.id,
        source=source,
        local_frame=local_frame,
        notes=notes,
    )


def link_tooth_meshes(
    tooth_assets: dict[ToothId, MeshAsset],
    *,
    source: MeshProvenance = MeshProvenance.MANUAL,
) -> list[SegmentedToothMesh]:
    return [
        link_tooth_mesh(tooth=tooth, mesh_asset=asset, source=source)
        for tooth, asset in sorted(tooth_assets.items(), key=lambda item: item[0].value)
    ]
