"""Compose evidence and workflow states without collapsing them into approval."""
from orthoplan.evaluation.finding import Finding, FindingProvenance, FindingSeverity
from orthoplan.evaluation.intake_cbct import cbct_records
from orthoplan.evaluation.intake_records import segmentation_records, surface_records
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.readiness import ArtifactState, IntakeReadiness, PlanCheckState
from orthoplan.printing import PrintExportStatus


def build_intake_readiness(
    plan: TreatmentPlan, findings: list[Finding], print_status: PrintExportStatus,
) -> IntakeReadiness:
    warnings = sum(f.provenance == FindingProvenance.RULE and
                   f.severity == FindingSeverity.WARNING for f in findings)
    if not plan.stages:
        status, detail = "no_stages", "No staged proposal exists to check."
    elif not plan.scale_confirmed:
        status, detail = "limited", "Unconfirmed scan units limit movement checks."
    elif warnings:
        status, detail = "findings_to_review", f"{warnings} deterministic warning(s) need review."
    else:
        status, detail = "checks_completed", "Configured checks ran; unresolved record gaps remain separate."
    return IntakeReadiness(
        records=[*surface_records(plan), *segmentation_records(plan), *cbct_records(plan)],
        plan_consistency=PlanCheckState(status=status, detail=detail, warning_count=warnings),
        artifacts=ArtifactState(
            status="prerequisites_met" if print_status.ready else "blocked",
            blockers=print_status.blockers,
        ),
    )
