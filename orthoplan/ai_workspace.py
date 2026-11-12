"""Provider-neutral, structured description of the workspace and scan inventory.

Describes serialized geometry metadata, not raw surfaces or filesystem access.
"""
from __future__ import annotations

from orthoplan.model.plan import TreatmentPlan


def workspace_context(plan: TreatmentPlan) -> dict:
    assets = {asset.id: asset for asset in plan.mesh_assets}
    return {
        "coordinate_frame": plan.coordinate_frame.model_dump(mode="json"),
        "scans": [{"id": scan.asset.id, "arch": scan.arch, "format": scan.asset.format,
                   "geometry_kind": scan.asset.geometry_kind, "units": scan.asset.units,
                   "vertices": scan.asset.vertex_count, "faces": scan.asset.face_count,
                   "bounds": scan.asset.bounds.model_dump() if scan.asset.bounds else None,
                   "quality": scan.asset.quality.model_dump(mode="json") if scan.asset.quality else None}
                  for scan in plan.scans],
        "teeth": [{"fdi": link.tooth.value, "reviewed": link.reviewed,
                   "asset_id": link.mesh_asset_id,
                   "bounds": assets[link.mesh_asset_id].bounds.model_dump()
                   if link.mesh_asset_id in assets and assets[link.mesh_asset_id].bounds else None}
                  for link in plan.tooth_meshes],
        "capabilities": {
            "read": ["plan snapshot", "scan metadata and bounds", "tooth links and review state",
                     "authored stages", "timeline", "deterministic findings", "record metadata"],
            "edit": "An explicit selected-tooth X/Y translation can be previewed, then applied by the user.",
            "workflow": ["Upload and confirm units", "Review tooth segmentation", "Select crown or FDI number",
                         "Preview explicit geometric change", "Apply or discard", "Scrub staged weeks"],
            "unavailable": ["raw mesh vertices and triangles", "scan images", "CBCT pixels",
                            "local filesystem access", "arbitrary application commands"],
        },
    }
