from __future__ import annotations

from math import hypot

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model import TreatmentPlan
from orthoplan.model.gaps import SURFACE_SCAN_LIMITATION
from orthoplan.model.plan import ToothDelta
from orthoplan.model.settings import AxisCaps

_CLINICIAN_QUESTION = (
    "Should staging, attachments, IPR, or additional imaging be considered before "
    "relying on this movement proposal?"
)


def evaluate_movement_caps(plan: TreatmentPlan) -> list[Finding]:
    if not plan.scale_confirmed:
        return [_scale_unconfirmed_notice()]

    caps = plan.settings.movement_caps
    findings: list[Finding] = []
    for stage in plan.stages:
        for delta in stage.deltas:
            findings.extend(_delta_cap_findings(stage.index, delta, caps.caps_for(delta.tooth.value)))
    return findings


def _delta_cap_findings(stage_index: int, delta: ToothDelta, caps: AxisCaps) -> list[Finding]:
    tooth_label = f"{delta.tooth.system} {delta.tooth.value}"
    findings: list[Finding] = []

    horizontal = hypot(delta.translate_x_mm, delta.translate_y_mm)
    if horizontal > caps.linear_mm:
        findings.append(
            _cap_warning(
                title=f"Stage {stage_index} exceeds configured linear cap",
                message=(
                    f"Tooth {tooth_label} has horizontal movement of {horizontal:.3f} mm "
                    f"(resultant magnitude), greater than the configured {caps.linear_mm} mm "
                    "per-stage cap."
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

    if abs(delta.rotate_tip_deg) > caps.angular_deg or abs(delta.rotate_torque_deg) > caps.angular_deg:
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


def _cap_warning(title: str, message: str, reference: str) -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.WARNING,
            category=FindingCategory.MECHANICS,
            provenance=FindingProvenance.RULE,
            title=title,
            message=message,
            code="movement-cap-exceeded",
            data_gap=SURFACE_SCAN_LIMITATION,
            clinician_question=_CLINICIAN_QUESTION,
            reference=reference,
        )
    )


def _scale_unconfirmed_notice() -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.NOTICE,
            category=FindingCategory.DATA_GAP,
            provenance=FindingProvenance.RULE,
            title="Movement-cap evaluation skipped: scan units unverified",
            message=(
                "One or more uploaded scans have unverified units, so per-stage "
                "movement caps cannot be compared in millimeters. Confirm scan units "
                "to enable cap evaluation."
            ),
            code="movement-cap-scale-unconfirmed",
            data_gap="Scan units are unverified; declared geometry scale cannot be trusted.",
            clinician_question="Have the scan units and scale been confirmed?",
        )
    )
