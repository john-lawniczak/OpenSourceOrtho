from __future__ import annotations

from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.settings import AxisCaps, MovementCaps, TreatmentSettings
from orthoplan.viz import build_stage_progress_frames


def _tooth(value: str = "11") -> ToothId:
    return ToothId(value=value)


def test_golden_cumulative_translation_is_exact_vector_sum() -> None:
    plan = TreatmentPlan(
        id="golden-translation",
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=_tooth(), translate_x_mm=0.125)]),
            Stage(
                index=1,
                deltas=[
                    ToothDelta(
                        tooth=_tooth(),
                        translate_x_mm=0.375,
                        translate_y_mm=-0.25,
                        translate_z_mm=0.1,
                    )
                ],
            ),
        ],
    )

    frames = build_stage_progress_frames(plan)
    pose = frames[1].poses[0]

    assert pose.translate_x_mm == 0.5
    assert pose.translate_y_mm == -0.25
    assert pose.translate_z_mm == 0.1


def test_golden_horizontal_cap_uses_euclidean_resultant_not_axis_max() -> None:
    plan = TreatmentPlan(
        id="golden-cap",
        settings=TreatmentSettings(
            movement_caps=MovementCaps(default=AxisCaps(linear_mm=0.5, reference="test cap"))
        ),
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=_tooth(), translate_x_mm=0.4, translate_y_mm=0.4)],
            )
        ],
    )

    findings = evaluate_movement_caps(plan)

    assert len(findings) == 1
    assert "0.566 mm" in findings[0].message
    assert "linear cap" in findings[0].title


def test_golden_vertical_and_angular_caps_are_checked_independently() -> None:
    plan = TreatmentPlan(
        id="golden-axis-caps",
        settings=TreatmentSettings(
            movement_caps=MovementCaps(
                default=AxisCaps(
                    linear_mm=1.0,
                    intrusion_extrusion_mm=0.2,
                    angular_deg=2.0,
                    rotation_deg=5.0,
                    reference="test cap",
                )
            )
        ),
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=_tooth(),
                        translate_z_mm=0.25,
                        rotate_tip_deg=2.5,
                        rotate_rotation_deg=6.0,
                    )
                ],
            )
        ],
    )

    titles = [finding.title for finding in evaluate_movement_caps(plan)]

    assert titles == [
        "Stage 0 exceeds configured vertical cap",
        "Stage 0 exceeds configured angular cap",
        "Stage 0 exceeds configured rotation cap",
    ]
