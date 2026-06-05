from __future__ import annotations

import pytest

from orthoplan.model import (
    AnatomicalDirection,
    AxisSemantics,
    CoordinateFrame,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.planning.transforms import ToothPose
from orthoplan.viz import build_stage_progress_frames


def test_cumulative_translation_matches_sum_for_many_sequences() -> None:
    tooth = ToothId(value="11")
    for seed in range(1, 25):
        deltas = []
        expected = [0.0, 0.0, 0.0]
        for index in range(4):
            dx = ((seed + index) % 5 - 2) * 0.05
            dy = ((seed * 2 + index) % 7 - 3) * 0.03
            dz = ((seed * 3 + index) % 3 - 1) * 0.02
            expected[0] += dx
            expected[1] += dy
            expected[2] += dz
            deltas.append(
                Stage(
                    index=index,
                    deltas=[
                        ToothDelta(
                            tooth=tooth,
                            translate_x_mm=dx,
                            translate_y_mm=dy,
                            translate_z_mm=dz,
                        )
                    ],
                )
            )
        pose = build_stage_progress_frames(TreatmentPlan(id=f"sum-{seed}", stages=deltas))[-1]
        pose = pose.poses[0]
        assert pose.translate_x_mm == pytest.approx(expected[0])
        assert pose.translate_y_mm == pytest.approx(expected[1])
        assert pose.translate_z_mm == pytest.approx(expected[2])


def test_pose_rejects_wrong_tooth_or_frame_delta() -> None:
    pose = ToothPose.from_delta(ToothDelta(tooth=ToothId(value="11")), rotation_renderable=False)

    with pytest.raises(ValueError, match="different tooth"):
        pose.apply_delta(ToothDelta(tooth=ToothId(value="21")))

    with pytest.raises(ValueError, match="different coordinate frames"):
        pose.apply_delta(ToothDelta(tooth=ToothId(value="11"), coordinate_frame="other"))


def test_global_anatomical_frame_makes_rotation_renderable_without_tooth_frame() -> None:
    frame = CoordinateFrame(
        name="trusted-anatomical",
        axes=AxisSemantics(
            x=AnatomicalDirection.MESIODISTAL,
            y=AnatomicalDirection.BUCCOLINGUAL,
            z=AnatomicalDirection.OCCLUSOGINGIVAL,
        ),
    )
    plan = TreatmentPlan(
        id="global-frame",
        coordinate_frame=frame,
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        rotate_tip_deg=1.0,
                        coordinate_frame="trusted-anatomical",
                    )
                ],
            )
        ],
    )

    frames = build_stage_progress_frames(plan)

    assert frames[0].rotation_renderable is True
    assert frames[0].poses[0].rotation_renderable is True
