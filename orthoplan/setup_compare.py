"""Deterministic setup comparison and live-restage preview helpers.

Phase 17 starts with pure data contracts so the UI can render side-by-side
setups without reimplementing movement math. A comparison is not approval; it is
just a diff between two plan snapshots plus an optional optimized restaging of
the edited setup.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.generate import generate_plan
from orthoplan.planning.timeline import project_timeline

_AXES = (
    "translate_x_mm",
    "translate_y_mm",
    "translate_z_mm",
    "rotate_tip_deg",
    "rotate_torque_deg",
    "rotate_rotation_deg",
)


class ToothMovementDiff(BaseModel):
    tooth: str
    before: dict[str, float]
    after: dict[str, float]
    delta: dict[str, float]


class SetupComparison(BaseModel):
    before_id: str
    after_id: str
    before_stage_count: int
    after_stage_count: int
    stage_count_delta: int
    changed_teeth: list[ToothMovementDiff] = Field(default_factory=list)
    added_teeth: list[str] = Field(default_factory=list)
    removed_teeth: list[str] = Field(default_factory=list)
    attachment_count_delta: int = 0
    ipr_count_delta: int = 0
    spacing_count_delta: int = 0
    fixed_tooth_count_delta: int = 0
    caveat: str = (
        "Setup comparison reports deterministic differences between plan snapshots. "
        "It does not decide whether either setup is safe, approved, clinically "
        "appropriate, or complete."
    )


class LiveRestageComparison(BaseModel):
    source: str
    requires_acknowledgement: bool
    before_timeline_days: int
    restaged_timeline_days: int
    comparison: SetupComparison
    warnings: list[str] = Field(default_factory=list)
    caveat: str


def compare_setups(before: TreatmentPlan, after: TreatmentPlan) -> SetupComparison:
    before_totals = _cumulative(before)
    after_totals = _cumulative(after)
    before_teeth = set(before_totals)
    after_teeth = set(after_totals)
    shared = sorted(before_teeth & after_teeth)
    changed = [
        _tooth_diff(tooth, before_totals[tooth], after_totals[tooth])
        for tooth in shared
        if _axis_delta(before_totals[tooth], after_totals[tooth])
    ]
    return SetupComparison(
        before_id=before.id,
        after_id=after.id,
        before_stage_count=len(before.stages),
        after_stage_count=len(after.stages),
        stage_count_delta=len(after.stages) - len(before.stages),
        changed_teeth=changed,
        added_teeth=sorted(after_teeth - before_teeth),
        removed_teeth=sorted(before_teeth - after_teeth),
        attachment_count_delta=len(after.attachments) - len(before.attachments),
        ipr_count_delta=len(after.interproximal_reductions) - len(before.interproximal_reductions),
        spacing_count_delta=len(after.planned_spacing) - len(before.planned_spacing),
        fixed_tooth_count_delta=len(after.fixed_teeth) - len(before.fixed_teeth),
    )


def live_restage_comparison(before: TreatmentPlan, edited: TreatmentPlan) -> LiveRestageComparison:
    generated = generate_plan(edited)
    comparison = compare_setups(before, generated.plan)
    return LiveRestageComparison(
        source=generated.source,
        requires_acknowledgement=generated.requires_acknowledgement,
        before_timeline_days=project_timeline(before).projected_duration_days,
        restaged_timeline_days=project_timeline(generated.plan).projected_duration_days,
        comparison=comparison,
        warnings=generated.warnings,
        caveat=generated.caveat,
    )


def compare_setups_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        before = TreatmentPlan.model_validate(payload.get("before"))
        after = TreatmentPlan.model_validate(payload.get("after"))
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}
    return {"ok": True, "comparison": compare_setups(before, after).model_dump(mode="json")}


def live_restage_comparison_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        before = TreatmentPlan.model_validate(payload.get("before"))
        edited = TreatmentPlan.model_validate(payload.get("edited"))
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}
    return {"ok": True, **live_restage_comparison(before, edited).model_dump(mode="json")}


def _cumulative(plan: TreatmentPlan) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for stage in plan.stages:
        for delta in stage.deltas:
            bucket = totals.setdefault(delta.tooth.value, {axis: 0.0 for axis in _AXES})
            for axis in _AXES:
                bucket[axis] += getattr(delta, axis)
    return totals


def _format_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(plan)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def _axis_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {
        axis: round(after.get(axis, 0.0) - before.get(axis, 0.0), 6)
        for axis in _AXES
        if abs(after.get(axis, 0.0) - before.get(axis, 0.0)) > 1e-9
    }


def _tooth_diff(
    tooth: str, before: dict[str, float], after: dict[str, float]
) -> ToothMovementDiff:
    return ToothMovementDiff(
        tooth=tooth,
        before={axis: round(before.get(axis, 0.0), 6) for axis in _AXES},
        after={axis: round(after.get(axis, 0.0), 6) for axis in _AXES},
        delta=_axis_delta(before, after),
    )
