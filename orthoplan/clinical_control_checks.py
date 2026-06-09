from __future__ import annotations

from orthoplan.model.clinical import MovementAxis
from orthoplan.model.plan import ToothDelta, TreatmentPlan


def active_fixed_tooth(plan: TreatmentPlan, tooth_value: str, stage_index: int) -> bool:
    """Whether a fixed-tooth control applies to this tooth at this stage."""

    return any(
        control.tooth.value == tooth_value and control.applies_to(stage_index)
        for control in plan.fixed_teeth
    )


def active_blocked_axes(plan: TreatmentPlan, tooth_value: str, stage_index: int) -> set[MovementAxis]:
    """Movement axes excluded for this tooth at this stage."""

    axes: set[MovementAxis] = set()
    for exclusion in plan.movement_exclusions:
        if exclusion.tooth.value != tooth_value:
            continue
        for axis in exclusion.axes:
            if exclusion.applies_to(stage_index, axis):
                axes.add(axis)
    return axes


def delta_violates_controls(plan: TreatmentPlan, delta: ToothDelta, stage_index: int) -> bool:
    """Shared clinical-control check for optimizer, rules, and correctness gates."""

    tooth_value = delta.tooth.value
    if active_fixed_tooth(plan, tooth_value, stage_index):
        return bool(delta.moved_axes())
    blocked_axes = active_blocked_axes(plan, tooth_value, stage_index)
    if "all" in blocked_axes:
        return bool(delta.moved_axes())
    return any(axis in blocked_axes for axis in delta.moved_axes())


def max_control_stage_end(plan: TreatmentPlan) -> int:
    """Last finite control endpoint, used to bound staging searches."""

    ends = [
        control.stage_end
        for control in [*plan.fixed_teeth, *plan.movement_exclusions]
        if control.stage_end is not None
    ]
    return max(ends, default=-1)
