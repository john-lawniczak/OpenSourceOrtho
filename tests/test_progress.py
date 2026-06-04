from __future__ import annotations

from orthoplan.model import MeshAsset, Stage, ToothDelta, ToothId, TreatmentPlan, UploadedScan
from orthoplan.planning.transforms import ToothPose
from orthoplan.viz import StageProgressFrame, build_stage_progress_frames


def test_progress_frames_are_cumulative() -> None:
    tooth = ToothId(value="11")
    plan = TreatmentPlan(
        id="visual-test",
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=tooth, translate_x_mm=0.2)]),
            Stage(index=1, deltas=[ToothDelta(tooth=tooth, translate_x_mm=0.3)]),
        ],
    )

    frames = build_stage_progress_frames(plan)

    assert frames[0].poses[0].translate_x_mm == 0.2
    assert frames[1].poses[0].translate_x_mm == 0.5


def test_pca_local_frame_does_not_make_rotation_renderable() -> None:
    from orthoplan.model import SegmentedToothMesh, ToothLocalFrame
    from orthoplan.model.assets import MeshAsset

    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    link = SegmentedToothMesh(
        tooth=ToothId(value="11"),
        mesh_asset_id="m11",
        local_frame=ToothLocalFrame(
            origin=(0, 0, 0), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))
        ),
    )
    plan = TreatmentPlan(
        id="rot",
        mesh_assets=[asset],
        tooth_meshes=[link],
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="m11", rotate_tip_deg=3.0),
                    ToothDelta(tooth=ToothId(value="21"), rotate_tip_deg=3.0),  # no frame
                ],
            )
        ],
    )
    frames = build_stage_progress_frames(plan)
    poses = {p.tooth.value: p for p in frames[0].poses}
    assert poses["11"].rotation_renderable is False  # PCA frame is approximate only
    assert poses["21"].rotation_renderable is False  # no frame
    assert frames[0].rotation_renderable is False


def test_non_approximate_local_frame_makes_rotation_renderable() -> None:
    from orthoplan.model import SegmentedToothMesh, ToothLocalFrame
    from orthoplan.model.assets import MeshAsset

    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    link = SegmentedToothMesh(
        tooth=ToothId(value="11"),
        mesh_asset_id="m11",
        local_frame=ToothLocalFrame(
            origin=(0, 0, 0),
            axes=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            source="trusted-anatomical-frame",
            approximate=False,
        ),
    )
    plan = TreatmentPlan(
        id="rot-trusted",
        mesh_assets=[asset],
        tooth_meshes=[link],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="m11", rotate_tip_deg=3.0)],
            )
        ],
    )

    frames = build_stage_progress_frames(plan)

    assert frames[0].poses[0].rotation_renderable is True
    assert frames[0].rotation_renderable is True


def test_progress_frames_mark_rotation_not_renderable_in_scan_frame() -> None:
    plan = TreatmentPlan(
        id="rot",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=3.0)])],
    )

    frames = build_stage_progress_frames(plan)

    # The Phase 1 scan frame cannot convert tip/torque, so rotation is reported
    # but flagged as not renderable.
    assert frames[0].rotation_renderable is False
    assert frames[0].poses[0].rotation_renderable is False
    assert "crown-centroid" in frames[0].poses[0].pivot


def test_progress_frames_include_data_gaps() -> None:
    plan = TreatmentPlan(
        id="visual-test",
        scans=[UploadedScan(asset=MeshAsset(id="scan", format="stl-ascii", vertex_count=3, face_count=1))],
        stages=[Stage(index=0)],
    )

    frames = build_stage_progress_frames(plan)

    assert "roots unavailable" in frames[0].data_gaps
    assert "CBCT unavailable" in frames[0].data_gaps
    assert any("units unverified" in gap for gap in frames[0].data_gaps)


def test_pose_ui_dict_covers_every_model_field() -> None:
    # Guards against silent contract drift: a new ToothPose field must appear in
    # the UI dict, not be dropped by a hand-written serializer.
    pose = ToothPose.from_delta(
        ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2), rotation_renderable=False
    )
    ui = pose.ui_dict()
    assert set(ui) == set(ToothPose.model_fields)
    assert ui["tooth"] == "11"  # flattened from the nested ToothId


def test_frame_ui_dict_covers_every_model_field() -> None:
    frame = StageProgressFrame(stage_index=0)
    ui = frame.ui_dict()
    assert set(ui) == set(StageProgressFrame.model_fields)
    assert isinstance(ui["poses"], list)
