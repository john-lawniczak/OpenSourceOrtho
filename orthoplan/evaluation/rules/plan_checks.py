"""Deterministic plan-level checks (Phase 4).

These complement the movement-cap and mesh-quality rules. They are about the
relationship between the planned movement and the declared data availability.

Several checks from the plan are already enforced at the MODEL layer at
construction time, so they need no runtime rule:
- stage-index contiguity (TreatmentPlan validator),
- duplicate tooth within a stage (Stage validator),
- mixed numbering systems / mixed coordinate frames (TreatmentPlan validator),
- a delta referencing another tooth's mesh (TreatmentPlan validator).
"""

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

# Movements where not seeing the root/bone is especially consequential: tipping,
# torquing, and intrusion/extrusion all swing or drive the (unseen) root and
# apex. Pure horizontal translation and pure long-axis rotation are excluded.
def _is_root_sensitive(delta: ToothDelta) -> bool:
    return (
        delta.rotate_tip_deg != 0.0
        or delta.rotate_torque_deg != 0.0
        or delta.translate_z_mm != 0.0
    )


def _moves(delta: ToothDelta) -> bool:
    return any(
        value != 0.0
        for value in (
            delta.translate_x_mm,
            delta.translate_y_mm,
            delta.translate_z_mm,
            delta.rotate_tip_deg,
            delta.rotate_torque_deg,
            delta.rotate_rotation_deg,
        )
    )


def evaluate_root_sensitive_movement(plan: TreatmentPlan) -> list[Finding]:
    """Flag tip/torque/intrusion movement when no root or bone imaging exists."""
    if plan.data.roots or plan.data.cbct:
        return []

    affected = [
        f"stage {stage.index} tooth {delta.tooth.value}"
        for stage in plan.stages
        for delta in stage.deltas
        if _is_root_sensitive(delta)
    ]
    if not affected:
        return []

    shown = ", ".join(affected[:8]) + (" ..." if len(affected) > 8 else "")
    return [
        lint_finding(
            Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.DATA_GAP,
                provenance=FindingProvenance.RULE,
                title="Root-sensitive movement planned without root or bone imaging",
                message=(
                    f"{len(affected)} movement(s) include tip, torque, or intrusion/extrusion "
                    f"({shown}), but neither root data nor CBCT is available. Surface scans "
                    "cannot show how these movements affect the root or surrounding bone."
                ),
                data_gap="Root and bone position are unavailable (no roots/CBCT).",
                clinician_question=(
                    "Should root/bone imaging (e.g. CBCT) be available before relying on "
                    "these tip, torque, or vertical movements?"
                ),
            )
        )
    ]


def evaluate_segmentation_presence(plan: TreatmentPlan) -> list[Finding]:
    """Note when movement is planned without any per-tooth segmentation."""
    has_movement = any(stage.deltas for stage in plan.stages)
    if not has_movement or plan.data.segmented_teeth or plan.tooth_meshes:
        return []
    return [
        lint_finding(
            Finding(
                severity=FindingSeverity.NOTICE,
                category=FindingCategory.DATA_GAP,
                provenance=FindingProvenance.RULE,
                title="Movement planned without per-tooth segmentation",
                message=(
                    "Tooth movements are defined but no per-tooth segmentation is declared or "
                    "linked, so visualization uses abstract proxies rather than per-tooth meshes."
                ),
                data_gap="Per-tooth segmentation is unavailable.",
            )
        )
    ]


def evaluate_no_movement(plan: TreatmentPlan) -> list[Finding]:
    """Note a plan that has stages but no actual tooth movement."""
    if not plan.stages:
        return []
    if any(_moves(delta) for stage in plan.stages for delta in stage.deltas):
        return []
    return [
        lint_finding(
            Finding(
                severity=FindingSeverity.INFO,
                category=FindingCategory.CONSISTENCY,
                provenance=FindingProvenance.RULE,
                title="Plan defines stages but no tooth movement",
                message=(
                    "The plan has one or more stages but every tooth delta is zero, so no "
                    "movement is proposed."
                ),
            )
        )
    ]
