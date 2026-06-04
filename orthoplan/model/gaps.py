"""Single source of data-gap strings.

Both the evaluation rules and the visualization layer must describe data gaps
identically, so the derivation lives here and is imported by both. This avoids
the prior duplication between ``viz`` and the movement-cap rule.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.assets import bounding_box_sanity
from orthoplan.model.plan import TreatmentPlan

# Surface-scan limitation reused by mechanics findings.
SURFACE_SCAN_LIMITATION = (
    "Surface scan geometry does not show roots, bone, or periodontal status."
)


class DataGapAction(BaseModel):
    gap: str
    impact: str
    next_step: str
    blocked_capabilities: list[str] = Field(default_factory=list)


def data_gaps(plan: TreatmentPlan) -> list[str]:
    """Observational list of interpretation-relevant data the plan does not have."""

    data = plan.data
    gaps: list[str] = []
    if not data.roots:
        gaps.append("roots unavailable")
    if not data.cbct:
        gaps.append("CBCT unavailable")
    if not data.periodontal_status:
        gaps.append("periodontal status unavailable")
    if not data.occlusion_scan:
        gaps.append("occlusion scan unavailable")
    if not data.clinician_notes:
        gaps.append("treatment notes unavailable")
    for scan in plan.scans:
        if note := bounding_box_sanity(scan.asset):
            gaps.append(note)
    return gaps


def data_gap_actions(plan: TreatmentPlan) -> list[DataGapAction]:
    """Structured handoff actions for missing data.

    These actions do not diagnose or decide treatment. They connect each data
    gap to the measurements or visualizations it limits, so callers can downgrade
    features and produce concrete follow-up questions.
    """

    data = plan.data
    actions: list[DataGapAction] = []
    if not data.roots:
        actions.append(_roots_action())
    if not data.cbct:
        actions.append(_cbct_action())
    if not data.periodontal_status:
        actions.append(_periodontal_action())
    if not data.occlusion_scan:
        actions.append(_occlusion_action())
    if not data.clinician_notes:
        actions.append(_notes_action())
    for scan in plan.scans:
        if note := bounding_box_sanity(scan.asset):
            actions.append(_scale_action(note))
    return actions


def _roots_action() -> DataGapAction:
    return DataGapAction(
        gap="roots unavailable",
        impact="Root position and root movement cannot be assessed from crown surfaces.",
        next_step=(
            "Ask whether root imaging or root-aware records are needed before relying "
            "on tip, torque, or vertical movement."
        ),
        blocked_capabilities=["root movement assessment"],
    )


def _cbct_action() -> DataGapAction:
    return DataGapAction(
        gap="CBCT unavailable",
        impact="Bone/root relationship and alveolar boundary checks are unavailable.",
        next_step="Ask whether CBCT is indicated for the planned movements and patient context.",
        blocked_capabilities=["bone boundary assessment"],
    )


def _periodontal_action() -> DataGapAction:
    return DataGapAction(
        gap="periodontal status unavailable",
        impact="Movement findings cannot account for periodontal support or risk factors.",
        next_step="Request periodontal status before interpreting movement feasibility.",
        blocked_capabilities=["periodontal risk assessment"],
    )


def _occlusion_action() -> DataGapAction:
    return DataGapAction(
        gap="occlusion scan unavailable",
        impact="Occlusal contacts and bite relationships are not checked.",
        next_step="Request occlusion/bite records if contact changes matter to the review.",
        blocked_capabilities=["occlusion contact assessment"],
    )


def _notes_action() -> DataGapAction:
    return DataGapAction(
        gap="treatment notes unavailable",
        impact="The engine has no treatment goals, constraints, or documented rationale.",
        next_step="Attach treatment notes or explicitly document the review question.",
        blocked_capabilities=["goal-aware review"],
    )


def _scale_action(note: str) -> DataGapAction:
    return DataGapAction(
        gap=note,
        impact="Millimeter measurements and movement-cap checks cannot be trusted without confirmed scale.",
        next_step="Confirm scan units and scale before using numeric movement findings.",
        blocked_capabilities=["movement cap evaluation", "measurement validation"],
    )
