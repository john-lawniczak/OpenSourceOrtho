"""Root/bone-aware review checks (run only behind trusted CBCT-derived anatomy).

These deterministic checks consume reviewed root centerlines/meshes, trusted
tooth axes, and alveolar bone records to flag root proximity, inter-root
collision, and cortical-boundary proximity, and to add root/bone context to
tip/torque/intrusion/extrusion/expansion movements. They are FAIL-CLOSED: when
registration, segmentation, or anatomy review quality is insufficient they emit
``cannot assess`` notices instead of guessing.

Review verdict vocabulary is intentionally limited to CONSISTENT, ISSUES, and
NOT_APPLICABLE - never a clinical clearance.
"""

from __future__ import annotations

from enum import StrEnum
from math import sqrt

from pydantic import BaseModel

from orthoplan.arch_contract import arch_from_tooth_value
from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model.plan import CBCT_RECORD_KINDS, TreatmentPlan
from orthoplan.model.review_tier import accepted_registration
from orthoplan.viz.progress import build_stage_progress_frames

ROOT_PROXIMITY_MM = 1.0
CORTICAL_MARGIN_MM = 1.0
_REFERENCE = "Root/bone proximity check on reviewed CBCT-derived anatomy."
_GAP = (
    "Root/bone checks use reviewed CBCT-derived geometry only; they do not model "
    "biological response, force systems, or material behavior."
)
_QUESTION = "Should root position, staging, or torque be reviewed for this movement?"


class RootBoneVerdict(StrEnum):
    CONSISTENT = "CONSISTENT"
    ISSUES = "ISSUES"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RootBoneReview(BaseModel):
    verdict: RootBoneVerdict
    findings: list[Finding] = []


def evaluate_root_bone_aware(plan: TreatmentPlan) -> list[Finding]:
    """Engine entry point: returns the root/bone-aware findings for a plan."""

    return root_bone_review(plan).findings


def root_bone_review(plan: TreatmentPlan) -> RootBoneReview:
    # Stay silent on plans that never asked for root/bone review (no CBCT). The
    # data-gap layer already reports "CBCT unavailable" for those.
    if not _cbct_attached(plan):
        return RootBoneReview(verdict=RootBoneVerdict.NOT_APPLICABLE, findings=[])

    blockers = _readiness_blockers(plan)
    if blockers:
        return RootBoneReview(
            verdict=RootBoneVerdict.NOT_APPLICABLE,
            findings=[_cannot_assess(blockers)],
        )

    anatomy = plan.derived_anatomy
    final_translate = _final_translate_by_tooth(plan)
    roots = _trusted_root_points(plan, final_translate)

    findings: list[Finding] = []
    findings.extend(_root_proximity_findings(roots))
    findings.extend(_cortical_findings(plan, roots))
    findings.extend(_movement_context_findings(plan, anatomy, final_translate))

    has_issue = any(f.severity == FindingSeverity.WARNING for f in findings)
    verdict = RootBoneVerdict.ISSUES if has_issue else RootBoneVerdict.CONSISTENT
    return RootBoneReview(verdict=verdict, findings=findings)


def _cbct_attached(plan: TreatmentPlan) -> bool:
    if plan.data.cbct:
        return True
    return any(record.kind in CBCT_RECORD_KINDS for record in plan.case_records)


def _readiness_blockers(plan: TreatmentPlan) -> list[str]:
    blockers: list[str] = []
    if accepted_registration(plan) is None:
        blockers.append("no accepted, quality-backed STL-to-CBCT registration")
    anatomy = plan.derived_anatomy
    if anatomy is None or not anatomy.has_trusted:
        blockers.append("no reviewed (trusted, in-field) CBCT-derived anatomy")
    if not plan.tooth_meshes:
        blockers.append("no reviewed per-tooth segmentation")
    return blockers


def _final_translate_by_tooth(plan: TreatmentPlan) -> dict[str, tuple[float, float, float]]:
    frames = build_stage_progress_frames(plan)
    if not frames:
        return {}
    last = frames[-1]
    return {
        pose.tooth.value: (pose.translate_x_mm, pose.translate_y_mm, pose.translate_z_mm)
        for pose in last.poses
    }


def _trusted_root_points(
    plan: TreatmentPlan, final_translate: dict[str, tuple[float, float, float]]
) -> dict[str, list[tuple[float, float, float]]]:
    """Per-tooth root sample points (centerlines), shifted by final movement."""

    anatomy = plan.derived_anatomy
    if anatomy is None:
        return {}
    out: dict[str, list[tuple[float, float, float]]] = {}
    for root in anatomy.roots:
        if not root.trusted or not root.centerline:
            continue
        dx, dy, dz = final_translate.get(root.tooth.value, (0.0, 0.0, 0.0))
        out[root.tooth.value] = [(p[0] + dx, p[1] + dy, p[2] + dz) for p in root.centerline]
    return out


def _min_distance(a: list[tuple[float, float, float]], b: list[tuple[float, float, float]]) -> float:
    best = float("inf")
    for pa in a:
        for pb in b:
            d = sqrt(sum((pa[i] - pb[i]) ** 2 for i in range(3)))
            best = min(best, d)
    return best


def _root_proximity_findings(roots: dict[str, list[tuple[float, float, float]]]) -> list[Finding]:
    findings: list[Finding] = []
    teeth = sorted(roots)
    for i, tooth_a in enumerate(teeth):
        for tooth_b in teeth[i + 1 :]:
            if arch_from_tooth_value(tooth_a) != arch_from_tooth_value(tooth_b):
                continue
            distance = _min_distance(roots[tooth_a], roots[tooth_b])
            if distance >= ROOT_PROXIMITY_MM:
                continue
            collision = distance <= 0.0
            findings.append(_warn(
                title=(
                    f"Roots {tooth_a} and {tooth_b} "
                    + ("intersect" if collision else "are in close proximity")
                ),
                message=(
                    f"Reviewed root centerlines for teeth {tooth_a} and {tooth_b} reach a "
                    f"minimum separation of {max(distance, 0.0):.2f} mm after planned "
                    f"movement (threshold {ROOT_PROXIMITY_MM:.2f} mm)."
                ),
                code="root-proximity",
            ))
    return findings


def _cortical_findings(
    plan: TreatmentPlan, roots: dict[str, list[tuple[float, float, float]]]
) -> list[Finding]:
    anatomy = plan.derived_anatomy
    bone_bounds = _trusted_bone_bounds(plan)
    if bone_bounds is None:
        if anatomy and anatomy.alveolar_bone:
            return [_cannot_assess(["alveolar bone geometry is attached but has no usable surface bounds"])]
        return [_cannot_assess(["no reviewed alveolar bone surface for cortical proximity"])]
    (lo, hi) = bone_bounds
    findings: list[Finding] = []
    for tooth, points in roots.items():
        margin = _outside_margin(points, lo, hi)
        if margin > CORTICAL_MARGIN_MM:
            findings.append(_warn(
                title=f"Root {tooth} approaches or exceeds the cortical boundary",
                message=(
                    f"Reviewed root for tooth {tooth} extends about {margin:.2f} mm beyond the "
                    f"reviewed alveolar bone boundary after planned movement (margin "
                    f"{CORTICAL_MARGIN_MM:.2f} mm)."
                ),
                code="cortical-proximity",
            ))
    return findings


def _trusted_bone_bounds(plan: TreatmentPlan):
    anatomy = plan.derived_anatomy
    if anatomy is None:
        return None
    assets = {a.id: a for a in plan.mesh_assets}
    assets.update({s.asset.id: s.asset for s in plan.scans})
    for bone in anatomy.alveolar_bone:
        if bone.trusted and bone.mesh_asset_id:
            asset = assets.get(bone.mesh_asset_id)
            if asset and asset.bounds:
                return (asset.bounds.min_xyz, asset.bounds.max_xyz)
    return None


def _outside_margin(points, lo, hi) -> float:
    """Largest distance any point lies outside the bone bounding box (0 if inside)."""

    worst = 0.0
    for p in points:
        for axis in range(3):
            below = lo[axis] - p[axis]
            above = p[axis] - hi[axis]
            worst = max(worst, below, above)
    return worst


_CONTEXT_AXES = (
    ("rotate_tip_deg", "tip"),
    ("rotate_torque_deg", "torque"),
    ("translate_z_mm", "intrusion/extrusion"),
    ("translate_x_mm", "lateral/expansion"),
)


def _movement_context_findings(plan: TreatmentPlan, anatomy, final_translate) -> list[Finding]:
    if anatomy is None:
        return []
    root_teeth = anatomy.trusted_root_teeth()
    axis_teeth = anatomy.trusted_axis_teeth()
    context_teeth = root_teeth | axis_teeth
    findings: list[Finding] = []
    for tooth in sorted(context_teeth):
        moved = [label for field, label in _CONTEXT_AXES if abs(_total_axis(plan, tooth, field)) > 0]
        if not moved:
            continue
        findings.append(lint_finding(Finding(
            severity=FindingSeverity.INFO,
            category=FindingCategory.EDUCATION,
            provenance=FindingProvenance.RULE,
            title=f"Root/bone context available for tooth {tooth}",
            message=(
                f"Tooth {tooth} has planned {', '.join(moved)} movement and reviewed "
                "root/axis anatomy, so root and bone context can inform the review of "
                "this movement."
            ),
            code="root-bone-context",
        )))
    return findings


def _total_axis(plan: TreatmentPlan, tooth: str, field: str) -> float:
    total = 0.0
    for stage in plan.stages:
        for delta in stage.deltas:
            if delta.tooth.value == tooth:
                total += getattr(delta, field, 0.0)
    return total


def _warn(title: str, message: str, code: str) -> Finding:
    return lint_finding(Finding(
        severity=FindingSeverity.WARNING,
        category=FindingCategory.MECHANICS,
        provenance=FindingProvenance.RULE,
        title=title,
        message=message,
        code=code,
        data_gap=_GAP,
        clinician_question=_QUESTION,
        reference=_REFERENCE,
    ))


def _cannot_assess(blockers: list[str]) -> Finding:
    return lint_finding(Finding(
        severity=FindingSeverity.NOTICE,
        category=FindingCategory.DATA_GAP,
        provenance=FindingProvenance.RULE,
        title="Root/bone-aware checks cannot be assessed",
        message=(
            "Root/bone-aware checks did not run because: "
            + "; ".join(blockers)
            + ". Provide accepted registration, reviewed segmentation, and reviewed "
            "in-field anatomy to enable them."
        ),
        code="root-bone-not-applicable",
        data_gap=_GAP,
    ))
