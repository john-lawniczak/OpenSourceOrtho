from __future__ import annotations

from orthoplan.model import MeshAsset, SegmentedToothMesh, Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.planning.mesh_transform import build_transformed_mesh_frames


def test_transformed_mesh_frames_apply_cumulative_translation() -> None:
    asset = MeshAsset(id="mesh-11", format="stl-ascii", vertex_count=1, face_count=1)
    plan = TreatmentPlan(
        id="mesh-transform",
        mesh_assets=[asset],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)]),
            Stage(index=1, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_y_mm=0.3)]),
        ],
    )

    frames = build_transformed_mesh_frames(plan, {"mesh-11": [(1.0, 2.0, 3.0)]})

    assert frames[0].meshes[0].vertices == [(1.2, 2.0, 3.0)]
    assert frames[1].meshes[0].vertices == [(1.2, 2.3, 3.0)]


def test_transformed_mesh_frames_report_missing_external_vertices() -> None:
    asset = MeshAsset(id="mesh-11", format="stl-ascii", vertex_count=1, face_count=1)
    plan = TreatmentPlan(
        id="mesh-transform",
        mesh_assets=[asset],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"))])],
    )

    frames = build_transformed_mesh_frames(plan, {})

    assert frames[0].meshes == []
    assert frames[0].missing_mesh_asset_ids == ["mesh-11"]
