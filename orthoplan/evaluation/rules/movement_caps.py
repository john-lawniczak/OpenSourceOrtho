from __future__ import annotations

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model import TreatmentPlan
from orthoplan.model.plan import ToothDelta
from orthoplan.model.settings import MovementCaps


def evaluate_movement_caps(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    caps = plan.settings.movement_caps

    for stage in plan.stages:
        for delta in stage.deltas:
            findings.extend(_delta_cap_findings(stage.index, delta, caps))

    return findings


def _delta_cap_findings(stage_index: int, delta: ToothDelta, caps: MovementCaps) -> list[Finding]:
    tooth_label = f"{delta.tooth.system} {delta.tooth.value}"
    findings: list[Finding] = []

    if _exceeds_horizontal_cap(delta, caps):
        findings.append(
            _cap_warning(
                title=f"Stage {stage_index} exceeds configured linear cap",
                message=(
                    f"Tooth {tooth_label} has horizontal movement greater than "
                    f"the configured {caps.linear_mm} mm per-stage cap."
                ),
                reference=caps.reference,
            )
        )

    if abs(delta.translate_z_mm) > caps.intrusion_extrusion_mm:
        findings.append(
            _cap_warning(
                title=f"Stage {stage_index} exceeds configured vertical cap",
                message=(
                    f"Tooth {tooth_label} has vertical movement greater than "
                    f"the configured {caps.intrusion_extrusion_mm} mm per-stage cap."
                ),
                reference=caps.reference,
            )
        )

    if _exceeds_angular_cap(delta, caps):
        findings.append(
            _cap_warning(
                title=f"Stage {stage_index} exceeds configured angular cap",
                message=(
                    f"Tooth {tooth_label} has tip or torque greater than "
                    f"the configured {caps.angular_deg} degree per-stage cap."
                ),
                reference=caps.reference,
            )
        )

    if abs(delta.rotate_rotation_deg) > caps.rotation_deg:
        findings.append(
            _cap_warning(
                title=f"Stage {stage_index} exceeds configured rotation cap",
                message=(
                    f"Tooth {tooth_label} has rotation greater than "
                    f"the configured {caps.rotation_deg} degree per-stage cap."
                ),
                reference=caps.reference,
            )
        )

    return findings


def _exceeds_horizontal_cap(delta: ToothDelta, caps: MovementCaps) -> bool:
    return abs(delta.translate_x_mm) > caps.linear_mm or abs(delta.translate_y_mm) > caps.linear_mm


def _exceeds_angular_cap(delta: ToothDelta, caps: MovementCaps) -> bool:
    return abs(delta.rotate_tip_deg) > caps.angular_deg or abs(delta.rotate_torque_deg) > caps.angular_deg


def _cap_warning(title: str, message: str, reference: str) -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.WARNING,
            category=FindingCategory.MECHANICS,
            provenance=FindingProvenance.RULE,
            title=title,
            message=message,
            data_gap="Surface scan geometry does not show roots, bone, or periodontal status.",
            clinician_question=(
                "Does the treating clinician want to adjust staging, attachments, IPR, "
                "or require additional imaging before relying on this movement proposal?"
            ),
            reference=reference,
        )
    )
