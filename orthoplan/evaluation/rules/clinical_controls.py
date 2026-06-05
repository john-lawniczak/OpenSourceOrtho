from __future__ import annotations

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model.plan import ToothDelta, TreatmentPlan

_CLINICAL_CONTROL_GAP = (
    "Clinical control metadata is declared, but expression depends on aligner fit, "
    "attachment design, material, compliance, and anatomy not proven by this plan."
)
_QUESTION = "Should the clinician revise the controls, staging, or records before relying on this setup?"
_REFERENCE = "Clinician-authored clinical controls in TreatmentPlan."


def evaluate_clinical_controls(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_fixed_tooth_findings(plan))
    findings.extend(_movement_exclusion_findings(plan))
    findings.extend(_attachment_dependency_findings(plan))
    findings.extend(_ipr_spacing_findings(plan))
    return findings


def _fixed_tooth_findings(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    fixed = plan.fixed_teeth
    if not fixed:
        return findings
    for stage in plan.stages:
        for delta in stage.deltas:
            if not _delta_moves(delta):
                continue
            controls = [item for item in fixed if item.tooth.value == delta.tooth.value and item.applies_to(stage.index)]
            if controls:
                findings.append(
                    _warning(
                        FindingCategory.CONSISTENCY,
                        f"Stage {stage.index} moves tooth marked fixed",
                        (
                            f"Tooth {delta.tooth.value} has movement in stage {stage.index}, "
                            "but a fixed-tooth control applies to that stage."
                        ),
                    )
                )
    return findings


def _movement_exclusion_findings(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    exclusions = plan.movement_exclusions
    if not exclusions:
        return findings
    for stage in plan.stages:
        for delta in stage.deltas:
            for axis in delta.moved_axes():
                controls = [
                    item
                    for item in exclusions
                    if item.tooth.value == delta.tooth.value and item.applies_to(stage.index, axis)
                ]
                if controls:
                    findings.append(
                        _warning(
                            FindingCategory.CONSISTENCY,
                            f"Stage {stage.index} uses excluded movement axis",
                            (
                                f"Tooth {delta.tooth.value} has {axis.replace('_', ' ')} movement "
                                f"in stage {stage.index}, but that axis is excluded by clinical controls."
                            ),
                        )
                    )
    return findings


def _attachment_dependency_findings(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    attachments_by_tooth = {}
    for attachment in plan.attachments:
        attachments_by_tooth.setdefault(attachment.tooth.value, []).append(attachment)

    for stage in plan.stages:
        for delta in stage.deltas:
            if not _likely_attachment_dependent(delta):
                continue
            active = [
                item
                for item in attachments_by_tooth.get(delta.tooth.value, [])
                if item.applies_to(stage.index)
            ]
            if not active:
                findings.append(
                    _notice(
                        FindingCategory.CLINICIAN_QUESTION,
                        f"Stage {stage.index} has movement without attachment metadata",
                        (
                            f"Tooth {delta.tooth.value} includes rotation, torque, tip, or vertical "
                            "movement commonly reviewed with attachment strategy, but no active "
                            "attachment is declared for that tooth and stage."
                        ),
                    )
                )
    return findings


def _ipr_spacing_findings(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    if (plan.interproximal_reductions or plan.planned_spacing) and not (
        plan.data.segmented_teeth or plan.tooth_meshes
    ):
        findings.append(
            _notice(
                FindingCategory.DATA_GAP,
                "IPR or spacing planned without segmentation",
                (
                    "Interproximal reduction or residual spacing is declared, but no per-tooth "
                    "segmentation is available. Contact locations and tooth surfaces cannot be "
                    "verified from the current plan data."
                ),
            )
        )

    for ipr in plan.interproximal_reductions:
        if ipr.amount_mm > 0.5:
            findings.append(
                _warning(
                    FindingCategory.MECHANICS,
                    "IPR amount exceeds conservative review threshold",
                    (
                        f"IPR of {ipr.amount_mm:.2f} mm is planned between {ipr.tooth_a.value} "
                        f"and {ipr.tooth_b.value}. This exceeds the 0.50 mm per-contact review "
                        "threshold configured in this rule."
                    ),
                    reference="Conservative deterministic IPR review threshold: 0.50 mm per contact.",
                )
            )
    return findings


def _delta_moves(delta: ToothDelta) -> bool:
    return bool(delta.moved_axes())


def _likely_attachment_dependent(delta: ToothDelta) -> bool:
    return any(
        value != 0.0
        for value in (
            delta.translate_z_mm,
            delta.rotate_tip_deg,
            delta.rotate_torque_deg,
            delta.rotate_rotation_deg,
        )
    )


def _notice(category: FindingCategory, title: str, message: str) -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.NOTICE,
            category=category,
            provenance=FindingProvenance.RULE,
            title=title,
            message=message,
        )
    )


def _warning(
    category: FindingCategory,
    title: str,
    message: str,
    *,
    reference: str | None = None,
) -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.WARNING,
            category=category,
            provenance=FindingProvenance.RULE,
            title=title,
            message=message,
            data_gap=_CLINICAL_CONTROL_GAP,
            clinician_question=_QUESTION,
            reference=reference or _REFERENCE,
        )
    )
