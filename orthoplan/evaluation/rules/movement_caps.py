from __future__ import annotations

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model import TreatmentPlan


def evaluate_movement_caps(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    caps = plan.settings.movement_caps

    for stage in plan.stages:
        for delta in stage.deltas:
            tooth_label = f"{delta.tooth.system} {delta.tooth.value}"
            linear_values = [
                abs(delta.translate_x_mm),
                abs(delta.translate_y_mm),
            ]
            vertical_value = abs(delta.translate_z_mm)
            angular_values = [
                abs(delta.rotate_tip_deg),
                abs(delta.rotate_torque_deg),
            ]
            rotation_value = abs(delta.rotate_rotation_deg)

            if any(value > caps.linear_mm for value in linear_values):
                findings.append(
                    _cap_warning(
                        title=f"Stage {stage.index} exceeds configured linear cap",
                        message=(
                            f"Tooth {tooth_label} has horizontal movement greater than "
                            f"the configured {caps.linear_mm} mm per-stage cap."
                        ),
                        reference=caps.reference,
                    )
                )

            if vertical_value > caps.intrusion_extrusion_mm:
                findings.append(
                    _cap_warning(
                        title=f"Stage {stage.index} exceeds configured vertical cap",
                        message=(
                            f"Tooth {tooth_label} has vertical movement greater than "
                            f"the configured {caps.intrusion_extrusion_mm} mm per-stage cap."
                        ),
                        reference=caps.reference,
                    )
                )

            if any(value > caps.angular_deg for value in angular_values):
                findings.append(
                    _cap_warning(
                        title=f"Stage {stage.index} exceeds configured angular cap",
                        message=(
                            f"Tooth {tooth_label} has tip or torque greater than "
                            f"the configured {caps.angular_deg} degree per-stage cap."
                        ),
                        reference=caps.reference,
                    )
                )

            if rotation_value > caps.rotation_deg:
                findings.append(
                    _cap_warning(
                        title=f"Stage {stage.index} exceeds configured rotation cap",
                        message=(
                            f"Tooth {tooth_label} has rotation greater than "
                            f"the configured {caps.rotation_deg} degree per-stage cap."
                        ),
                        reference=caps.reference,
                    )
                )

    return findings


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

