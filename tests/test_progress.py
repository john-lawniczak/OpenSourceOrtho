from __future__ import annotations

from orthoplan.model import MeshAsset, Stage, ToothDelta, ToothId, TreatmentPlan, UploadedScan
from orthoplan.viz import build_stage_progress_frames


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
