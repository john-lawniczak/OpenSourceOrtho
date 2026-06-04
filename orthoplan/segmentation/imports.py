"""Imported per-tooth segmentation (Phase 3).

Inspects a set of per-tooth STL files and returns plan-ready mesh assets plus
their tooth links. No ML segmentation: this is the imported/manual path where
each tooth already has its own mesh file.
"""

from __future__ import annotations

from pathlib import Path

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.model.assets import MeshAsset, MeshProvenance
from orthoplan.model.plan import SegmentedToothMesh, ToothId
from orthoplan.planning.mesh_frame import compute_local_frame
from orthoplan.segmentation.manual import link_tooth_mesh


def import_segmented_meshes(
    tooth_paths: dict[ToothId, str | Path],
    *,
    provenance: MeshProvenance = MeshProvenance.IMPORTED,
) -> tuple[list[MeshAsset], list[SegmentedToothMesh]]:
    """Inspect one STL per tooth and produce (mesh_assets, tooth_meshes).

    Drop the results straight into ``TreatmentPlan(mesh_assets=..., tooth_meshes=...)``.
    Raises if two teeth resolve to the same mesh content (identical asset id),
    since a tooth link must be unambiguous.
    """

    assets: list[MeshAsset] = []
    links: list[SegmentedToothMesh] = []
    seen_ids: dict[str, str] = {}

    for tooth, path in sorted(tooth_paths.items(), key=lambda item: item[0].value):
        asset, vertices = read_stl_geometry(path, provenance=provenance)
        if asset.id in seen_ids:
            raise ValueError(
                f"teeth {seen_ids[asset.id]} and {tooth.value} resolve to identical mesh "
                f"content (asset {asset.id}); each tooth needs a distinct mesh"
            )
        seen_ids[asset.id] = tooth.value
        assets.append(asset)
        links.append(
            link_tooth_mesh(
                tooth=tooth,
                mesh_asset=asset,
                source=provenance,
                local_frame=compute_local_frame(vertices),
            )
        )

    return assets, links
