"""Root-apex sweep estimate for planned angulation (root-aware movement check).

The visualization pivot is the crown centroid, so a crown that tips or torques
by theta sweeps its apex by about ``root_length * sin(theta)`` - a purely
geometric rigid-body estimate (no bone, ligament, or biology). Crown
translation moves the apex 1:1 and is already covered by movement caps, so only
the angular sweep is estimated here. Runs only on TRUSTED (human-reviewed,
in-field) root centerlines; see ``root_bone`` for the readiness gating.
"""

from __future__ import annotations

from math import radians, sin, sqrt

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model.plan import TreatmentPlan

# Heuristic review threshold for the estimated apex sweep from planned
# angulation (tip/torque) about the crown-centroid pivot. A literature-style
# caution level for staging review, NOT a clinical limit or clearance.
APEX_DISPLACEMENT_WARN_MM = 2.0

_REFERENCE = "Geometric apex-sweep estimate on reviewed CBCT-derived root centerlines."
_GAP = (
    "The apex estimate is rigid-body geometry about the crown-centroid pivot. It does "
    "not model the true center of resistance, bone, ligament, force systems, or biology."
)
_QUESTION = "Should the planned tip/torque staging be reviewed against root length?"


def apex_displacement_findings(plan: TreatmentPlan, anatomy) -> list[Finding]:
    """INFO documents each trusted tooth's estimated apex sweep; WARNING flags excess."""

    if anatomy is None:
        return []
    findings: list[Finding] = []
    for root in anatomy.roots:
        if not root.trusted or len(root.centerline) < 2:
            continue
        tooth = root.tooth.value
        tip = total_axis(plan, tooth, "rotate_tip_deg")
        torque = total_axis(plan, tooth, "rotate_torque_deg")
        # Small-angle composition of two orthogonal angulations.
        angle_deg = sqrt(tip * tip + torque * torque)
        if angle_deg <= 0:
            continue
        length = _polyline_length(root.centerline)
        if length <= 0:
            continue
        sweep = length * abs(sin(radians(angle_deg)))
        findings.append(_apex_finding(tooth, tip, torque, angle_deg, length, sweep))
    return findings


def _apex_finding(
    tooth: str, tip: float, torque: float, angle_deg: float, length: float, sweep: float
) -> Finding:
    message = (
        f"Tooth {tooth} plans {angle_deg:.1f} deg of total angulation "
        f"(tip {tip:.1f} deg, torque {torque:.1f} deg). With the reviewed "
        f"root length of {length:.1f} mm pivoting at the crown centroid, the "
        f"root apex would sweep about {sweep:.2f} mm. Geometric estimate "
        "only - not a biomechanical or biological prediction."
    )
    if sweep > APEX_DISPLACEMENT_WARN_MM:
        return lint_finding(Finding(
            severity=FindingSeverity.WARNING,
            category=FindingCategory.MECHANICS,
            provenance=FindingProvenance.RULE,
            title=f"Estimated root-apex sweep for tooth {tooth} exceeds review threshold",
            message=message + f" Review threshold: {APEX_DISPLACEMENT_WARN_MM:.1f} mm.",
            code="root-apex-displacement",
            data_gap=_GAP,
            clinician_question=_QUESTION,
            reference=_REFERENCE,
        ))
    return lint_finding(Finding(
        severity=FindingSeverity.INFO,
        category=FindingCategory.MECHANICS,
        provenance=FindingProvenance.RULE,
        title=f"Estimated root-apex sweep for tooth {tooth}",
        message=message,
        code="root-apex-displacement",
        data_gap=_GAP,
        reference=_REFERENCE,
    ))


def total_axis(plan: TreatmentPlan, tooth: str, field: str) -> float:
    """Total planned movement on one delta field for one tooth, across all stages."""

    total = 0.0
    for stage in plan.stages:
        for delta in stage.deltas:
            if delta.tooth.value == tooth:
                total += getattr(delta, field, 0.0)
    return total


def _polyline_length(points) -> float:
    total = 0.0
    for start, end in zip(points, points[1:]):
        total += sqrt(sum((end[i] - start[i]) ** 2 for i in range(3)))
    return total
