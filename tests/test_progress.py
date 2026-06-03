from __future__ import annotations

from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.viz import build_stage_progress_frames


def test_progress_frames_are_cumulative() -> None:
    tooth = ToothId(value="11")
    plan = TreatmentPlan(
        id="visual-test",
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=tooth, arch="maxillary", translate_x_mm=0.2)],
            ),
            Stage(
                index=1,
                deltas=[ToothDelta(tooth=tooth, arch="maxillary", translate_x_mm=0.3)],
            ),
        ],
    )

    frames = build_stage_progress_frames(plan)

    assert frames[0].poses[0].translate_x_mm == 0.2
    assert frames[1].poses[0].translate_x_mm == 0.5


def test_progress_frames_include_data_gaps() -> None:
    plan = TreatmentPlan(id="visual-test", stages=[Stage(index=0)])

    frames = build_stage_progress_frames(plan)

    assert "roots unavailable" in frames[0].data_gaps
    assert "CBCT unavailable" in frames[0].data_gaps
