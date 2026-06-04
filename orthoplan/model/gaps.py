"""Single source of data-gap strings.

Both the evaluation rules and the visualization layer must describe data gaps
identically, so the derivation lives here and is imported by both. This avoids
the prior duplication between ``viz`` and the movement-cap rule.
"""

from __future__ import annotations

from orthoplan.model.assets import bounding_box_sanity
from orthoplan.model.plan import TreatmentPlan

# Surface-scan limitation reused by mechanics findings.
SURFACE_SCAN_LIMITATION = (
    "Surface scan geometry does not show roots, bone, or periodontal status."
)


def data_gaps(plan: TreatmentPlan) -> list[str]:
    """Observational list of clinically relevant data the plan does not have."""

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
        gaps.append("clinician notes unavailable")
    for scan in plan.scans:
        if note := bounding_box_sanity(scan.asset):
            gaps.append(note)
    return gaps
