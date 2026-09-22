"""Deterministic correctness review for generated plans.

Split out of ``generation.py`` so the gateway stays small. Produces the explicit,
named checks that decide the orchestration verdict (CONSISTENT / ISSUES /
NOT_APPLICABLE) - never an approval.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from orthoplan.clinical_control_checks import delta_violates_controls
from orthoplan.model.plan import TreatmentPlan

CorrectnessVerdict = Literal["CONSISTENT", "ISSUES", "NOT_APPLICABLE"]

_AXES = (
    "translate_x_mm", "translate_y_mm", "translate_z_mm",
    "rotate_tip_deg", "rotate_torque_deg", "rotate_rotation_deg",
)


class PipelineStep(BaseModel):
    name: str
    status: Literal["ok", "warning", "skipped"] = "ok"
    detail: str = ""


class Check(BaseModel):
    """One named correctness check. ``gate`` checks fail the verdict; ``warning``
    and ``info`` checks are surfaced but do not flip CONSISTENT to ISSUES."""

    name: str
    passed: bool
    severity: Literal["gate", "warning", "info"] = "gate"
    detail: str = ""


def _cumulative_from_deltas(deltas) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for delta in deltas:
        bucket = totals.setdefault(delta.tooth.value, {a: 0.0 for a in _AXES})
        for axis in _AXES:
            bucket[axis] += getattr(delta, axis)
    return totals


def _cumulative(plan: TreatmentPlan) -> dict[str, dict[str, float]]:
    return _cumulative_from_deltas(d for stage in plan.stages for d in stage.deltas)


def _targets_reached_check(plan: TreatmentPlan, generated) -> Check:
    """Every non-blocked target tooth's cumulative movement must equal its target."""
    blocked = set(generated.blocked_teeth)
    want = _cumulative_from_deltas(generated.requested_targets)
    got = _cumulative(plan)
    mismatches = [
        tooth for tooth, target in want.items()
        if tooth not in blocked
        and any(abs(target[a] - got.get(tooth, {a2: 0.0 for a2 in _AXES})[a]) > 1e-6 for a in _AXES)
    ]
    detail = ("cumulative movement reaches every requested target" if not mismatches
              else f"targets not reached for: {', '.join(sorted(mismatches))}")
    return Check(name="targets-reached", passed=not mismatches, detail=detail)


def _control_violations(plan: TreatmentPlan) -> tuple[list[str], list[str]]:
    fixed_moved = sorted({
        delta.tooth.value
        for stage in plan.stages
        for delta in stage.deltas
        if any(
            control.tooth.value == delta.tooth.value and control.applies_to(stage.index)
            for control in plan.fixed_teeth
        )
        and delta.moved_axes()
    })
    excluded_moved = sorted({
        delta.tooth.value
        for stage in plan.stages
        for delta in stage.deltas
        if delta_violates_controls(plan, delta, stage.index)
        and not any(
            control.tooth.value == delta.tooth.value and control.applies_to(stage.index)
            for control in plan.fixed_teeth
        )
    })
    return fixed_moved, excluded_moved


def correctness_review(
    plan: TreatmentPlan, findings: list, generated
) -> tuple[CorrectnessVerdict, PipelineStep, list[Check], dict]:
    cap_violations = [f.title for f in findings if getattr(f, "code", None) == "movement-cap-exceeded"]
    collision_count = sum(
        1 for f in findings if getattr(f, "code", None) == "segmented-crown-bounds-overlap"
    )
    fixed_moved, excluded_moved = _control_violations(plan)
    contiguous = [s.index for s in plan.stages] == list(range(len(plan.stages)))

    metrics = {
        "cap_violations": len(cap_violations),
        "fixed_teeth_moved": fixed_moved,
        "excluded_teeth_moved": excluded_moved,
        "collision_count": collision_count,
    }
    if not plan.stages:
        step = PipelineStep(name="correctness-review", status="skipped", detail="No staging produced.")
        return "NOT_APPLICABLE", step, [], metrics

    checks = [
        Check(name="caps-respected", passed=not cap_violations,
              detail=f"{len(cap_violations)} per-stage cap violation(s)"),
        Check(name="fixed-teeth-unmoved", passed=not fixed_moved,
              detail=f"fixed teeth moved: {', '.join(fixed_moved) or 'none'}"),
        Check(name="exclusions-respected", passed=not excluded_moved,
              detail=f"excluded teeth moved: {', '.join(excluded_moved) or 'none'}"),
        _targets_reached_check(plan, generated),
        Check(name="stages-contiguous", passed=contiguous,
              detail="stage indexes are contiguous from 0" if contiguous else "non-contiguous stages"),
        Check(name="scale-confirmed", passed=plan.scale_confirmed, severity="warning",
              detail="scan units confirmed" if plan.scale_confirmed else "units unverified; caps not in mm"),
        Check(name="collisions-checked", passed=True, severity="info",
              detail=f"{collision_count} crown-bounds overlap(s) reported"
                     + ("" if plan.tooth_meshes else "; no segmented teeth, overlap check is vacuous")),
    ]
    verdict: CorrectnessVerdict = "ISSUES" if any(
        c.severity == "gate" and not c.passed for c in checks
    ) else "CONSISTENT"
    failed = [c.name for c in checks if c.severity == "gate" and not c.passed]
    detail = "all gate checks passed" if verdict == "CONSISTENT" else f"failed: {', '.join(failed)}"
    step = PipelineStep(name="correctness-review",
                        status="ok" if verdict == "CONSISTENT" else "warning", detail=detail)
    return verdict, step, checks, metrics
