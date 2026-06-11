"""Review-tier classification for a plan's evidence base.

A review tier names *what kind of records back a plan* and therefore what a
reader is allowed to trust. It is the single source of truth shared by the
browser UI (Phase 1 copy), export labeling (Phase 3), and the mobile handoff
(Phase 8), so all three describe the same plan identically.

Safety posture: tiers only ever *increase* with more reviewed evidence, and the
highest tier (``ROOT_BONE_AWARE``) is **fail-closed** - it is never returned from
crown/surface data or from mere ``DataAvailability`` flags. It requires accepted
STL-to-CBCT registration *and* reviewed CBCT-derived anatomy, which are produced
by later phases. Until those records exist, a CBCT attachment classifies as
``CBCT_ATTACHED`` (attached, not yet interpretable), never root/bone-aware.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from orthoplan.model.plan import TreatmentPlan

# Record kinds (see CaseRecordKind) grouped by what they unlock.
CBCT_RECORD_KINDS = {"cbct", "dicom"}
ENHANCED_RECORD_KINDS = {"photo", "radiograph", "note", "document"}


class ReviewTier(StrEnum):
    """Ordered from least to most evidence. Order matters for comparisons."""

    STL_ONLY = "stl-only"
    ENHANCED_RECORDS = "enhanced-records"
    CBCT_ATTACHED = "cbct-attached"
    ROOT_BONE_AWARE = "root-bone-aware"


_TIER_RANK = {
    ReviewTier.STL_ONLY: 0,
    ReviewTier.ENHANCED_RECORDS: 1,
    ReviewTier.CBCT_ATTACHED: 2,
    ReviewTier.ROOT_BONE_AWARE: 3,
}

_TIER_LABEL = {
    ReviewTier.STL_ONLY: "STL surface only",
    ReviewTier.ENHANCED_RECORDS: "STL + enhanced records",
    ReviewTier.CBCT_ATTACHED: "CBCT attached (not registered)",
    ReviewTier.ROOT_BONE_AWARE: "Root/bone-aware review",
}

_TIER_SUMMARY = {
    ReviewTier.STL_ONLY: (
        "Crown surface geometry only. No roots, bone, periodontal status, or "
        "occlusion. Findings are surface-level review aids, not diagnosis."
    ),
    ReviewTier.ENHANCED_RECORDS: (
        "Crown surfaces plus photos, radiographs, or notes for human context. "
        "The extra records are not registered to the scan and do not change "
        "geometry or movement generation."
    ),
    ReviewTier.CBCT_ATTACHED: (
        "A CBCT/DICOM volume is attached for reference only. It is not yet "
        "registered to the surface scan, so no root or bone geometry is trusted "
        "and root/bone checks stay unavailable."
    ),
    ReviewTier.ROOT_BONE_AWARE: (
        "CBCT is registered to the surface scan and root/bone anatomy has been "
        "reviewed. Root-proximity and bone-boundary context may be shown, still "
        "as a review aid and never as clinical clearance."
    ),
}


def root_bone_aware_ready(plan: TreatmentPlan) -> bool:
    """Whether a plan has accepted registration AND reviewed CBCT-derived anatomy.

    Fail-closed extension point. Phases 5-7 add the ``RegistrationTransform`` and
    reviewed-anatomy records this checks. Until then it is always ``False``: a
    CBCT attachment, ``DataAvailability.roots``/``cbct`` flags, or any surface
    data can NEVER on their own promote a plan to root/bone-aware.
    """

    registration = getattr(plan, "registrations", None) or []
    anatomy = getattr(plan, "derived_anatomy", None) or []
    if not registration or not anatomy:
        return False
    accepted_reg = any(getattr(r, "accepted", False) for r in registration)
    reviewed_anatomy = any(getattr(a, "reviewed", False) for a in anatomy)
    return accepted_reg and reviewed_anatomy


def _has_cbct(plan: TreatmentPlan) -> bool:
    if plan.data.cbct:
        return True
    return any(record.kind in CBCT_RECORD_KINDS for record in plan.case_records)


def _has_enhanced(plan: TreatmentPlan) -> bool:
    if plan.data.photos or plan.data.radiographs or plan.data.clinician_notes:
        return True
    return any(record.kind in ENHANCED_RECORD_KINDS for record in plan.case_records)


def review_tier(plan: TreatmentPlan) -> ReviewTier:
    """Classify a plan's evidence base into a single review tier."""

    if root_bone_aware_ready(plan):
        return ReviewTier.ROOT_BONE_AWARE
    if _has_cbct(plan):
        return ReviewTier.CBCT_ATTACHED
    if _has_enhanced(plan):
        return ReviewTier.ENHANCED_RECORDS
    return ReviewTier.STL_ONLY


class ReviewTierInfo(BaseModel):
    """Serializable tier description for UI/export/handoff surfaces."""

    tier: ReviewTier
    rank: int
    label: str
    summary: str
    root_bone_aware: bool


# Anatomy domains an STL-surface review can never resolve from crown geometry.
# Each stays unresolved until the plan reaches ROOT_BONE_AWARE (registration +
# reviewed CBCT anatomy). Listed explicitly so an exported report always names
# them rather than silently omitting what it cannot see.
_SURFACE_BLIND_DOMAINS = (
    ("roots", "Root geometry and root position are not visible in surface scans."),
    ("alveolar_bone", "Alveolar bone boundaries require registered, reviewed CBCT."),
    (
        "periodontal_status",
        "Periodontal support and risk are not derivable from crown surfaces.",
    ),
    ("occlusion", "Dynamic occlusion and contacts require occlusal records."),
    (
        "cbct_anatomy",
        "CBCT-derived anatomy requires registration and human review before use.",
    ),
)


def unresolved_surface_gaps(plan: TreatmentPlan) -> list[dict[str, str]]:
    """Anatomy domains an STL-surface plan cannot resolve at its current tier.

    Fail-closed: every blind domain is listed unless the plan is root/bone-aware.
    """

    if root_bone_aware_ready(plan):
        return []
    return [{"domain": domain, "reason": reason} for domain, reason in _SURFACE_BLIND_DOMAINS]


def review_tier_info(plan: TreatmentPlan) -> ReviewTierInfo:
    tier = review_tier(plan)
    return ReviewTierInfo(
        tier=tier,
        rank=_TIER_RANK[tier],
        label=_TIER_LABEL[tier],
        summary=_TIER_SUMMARY[tier],
        root_bone_aware=tier is ReviewTier.ROOT_BONE_AWARE,
    )


class CbctStatus(StrEnum):
    """Lifecycle of a CBCT attachment, surfaced in the case UI."""

    UNAVAILABLE = "unavailable"
    ATTACHED = "attached"
    VIEWED = "viewed"
    REGISTERED = "registered"
    ANATOMY_REVIEWED = "anatomy-reviewed"


def cbct_status(plan: TreatmentPlan) -> CbctStatus:
    """Server-derivable CBCT lifecycle state (the UI may overlay ``viewed``).

    Fail-closed: a CBCT attachment is ``ATTACHED`` until accepted registration
    (``REGISTERED``) and then reviewed anatomy (``ANATOMY_REVIEWED``) exist.
    """

    if not _has_cbct(plan):
        return CbctStatus.UNAVAILABLE
    if root_bone_aware_ready(plan):
        return CbctStatus.ANATOMY_REVIEWED
    registration = getattr(plan, "registrations", None) or []
    if any(getattr(r, "accepted", False) for r in registration):
        return CbctStatus.REGISTERED
    return CbctStatus.ATTACHED


class CbctHandoff(BaseModel):
    """A clean handoff to a trusted local DICOM viewer (e.g. 3D Slicer)."""

    status: CbctStatus
    available: bool
    viewer_suggestion: str
    instructions: str
    local_references: list[str] = Field(default_factory=list)


_SLICER_INSTRUCTIONS = (
    "Open the local CBCT/DICOM file(s) listed below in a trusted local viewer "
    "such as 3D Slicer (slicer.org) or your PACS workstation. OpenSource Ortho "
    "does not render CBCT volumes in the browser and never uploads them. Slice "
    "review (axial/coronal/sagittal) is performed in that viewer."
)


def cbct_handoff(plan: TreatmentPlan) -> CbctHandoff:
    status = cbct_status(plan)
    references = [
        record.local_reference
        for record in plan.case_records
        if record.kind in CBCT_RECORD_KINDS and record.local_reference
    ]
    available = status is not CbctStatus.UNAVAILABLE
    return CbctHandoff(
        status=status,
        available=available,
        viewer_suggestion="3D Slicer (https://www.slicer.org)",
        instructions=_SLICER_INSTRUCTIONS if available else "No CBCT/DICOM record is attached.",
        local_references=references,
    )
