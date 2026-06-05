from __future__ import annotations

import pytest

from orthoplan.evaluation.rules.clinical_controls import evaluate_clinical_controls
from orthoplan.model import (
    Attachment,
    FixedTooth,
    InterproximalReduction,
    MovementExclusion,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)


def test_fixed_tooth_control_flags_movement() -> None:
    plan = TreatmentPlan(
        id="fixed",
        fixed_teeth=[FixedTooth(tooth=ToothId(value="11"))],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)],
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert any("marked fixed" in finding.title for finding in findings)


def test_movement_exclusion_flags_matching_axis_only() -> None:
    plan = TreatmentPlan(
        id="excluded-axis",
        movement_exclusions=[
            MovementExclusion(tooth=ToothId(value="11"), axes={"rotation"}),
        ],
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        translate_x_mm=0.1,
                        rotate_rotation_deg=1.0,
                    )
                ],
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert len([finding for finding in findings if "excluded movement axis" in finding.title]) == 1


def test_attachment_metadata_suppresses_attachment_notice() -> None:
    plan = TreatmentPlan(
        id="attachment-present",
        attachments=[Attachment(tooth=ToothId(value="11"))],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_rotation_deg=1.0)],
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert not any("without attachment metadata" in finding.title for finding in findings)


def test_attachment_dependent_movement_without_attachment_is_noted() -> None:
    plan = TreatmentPlan(
        id="attachment-missing",
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_torque_deg=1.0)],
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert any("without attachment metadata" in finding.title for finding in findings)


def test_ipr_without_segmentation_is_noted() -> None:
    plan = TreatmentPlan(
        id="ipr-gap",
        interproximal_reductions=[
            InterproximalReduction(
                tooth_a=ToothId(value="11"),
                tooth_b=ToothId(value="21"),
                amount_mm=0.2,
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert any("without segmentation" in finding.title for finding in findings)


def test_large_ipr_is_warned() -> None:
    plan = TreatmentPlan(
        id="large-ipr",
        interproximal_reductions=[
            InterproximalReduction(
                tooth_a=ToothId(value="11"),
                tooth_b=ToothId(value="21"),
                amount_mm=0.6,
            )
        ],
    )

    findings = evaluate_clinical_controls(plan)

    assert any("IPR amount exceeds" in finding.title for finding in findings)


def test_ipr_teeth_must_be_distinct() -> None:
    with pytest.raises(ValueError, match="distinct"):
        InterproximalReduction(
            tooth_a=ToothId(value="11"),
            tooth_b=ToothId(value="11"),
            amount_mm=0.2,
        )
