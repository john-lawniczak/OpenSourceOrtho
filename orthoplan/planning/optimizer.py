from __future__ import annotations

from math import ceil, hypot

from pydantic import BaseModel, Field

from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.clinical import MovementAxis


class OptimizerIssue(BaseModel):
    tooth: str
    message: str


class OptimizedStagingResult(BaseModel):
    plan: TreatmentPlan
    issues: list[OptimizerIssue] = Field(default_factory=list)
    caveat: str = (
        "Deterministic staging splits authored movement into configured cap-sized increments. "
        "It is not a biological outcome model and does not replace clinician review."
    )


def optimize_staging(plan: TreatmentPlan) -> OptimizedStagingResult:
    """Return a cap-respecting staged copy of the plan where possible."""

    totals = _target_totals(plan)
    issues: list[OptimizerIssue] = []
    per_tooth_steps: dict[str, int] = {}
    allowed_totals: dict[str, ToothDelta] = {}

    for tooth_value, delta in totals.items():
        blocked_axes = _blocked_axes(plan, tooth_value)
        moved_blocked = [axis for axis in delta.moved_axes() if axis in blocked_axes or "all" in blocked_axes]
        fixed = any(control.tooth.value == tooth_value for control in plan.fixed_teeth)
        if fixed or moved_blocked:
            issues.append(
                OptimizerIssue(
                    tooth=tooth_value,
                    message="Movement omitted because fixed-tooth or movement-exclusion controls apply.",
                )
            )
            continue
        allowed_totals[tooth_value] = delta
        per_tooth_steps[tooth_value] = _steps_for_delta(plan, delta)

    stage_count = max(per_tooth_steps.values(), default=0)
    stages: list[Stage] = []
    for stage_index in range(stage_count):
        deltas = []
        for tooth_value, total in sorted(allowed_totals.items()):
            steps = per_tooth_steps[tooth_value]
            if stage_index >= steps:
                continue
            deltas.append(_split_delta(total, steps))
        stages.append(Stage(index=stage_index, deltas=deltas))

    return OptimizedStagingResult(plan=plan.model_copy(update={"stages": stages}), issues=issues)


def _target_totals(plan: TreatmentPlan) -> dict[str, ToothDelta]:
    totals: dict[str, ToothDelta] = {}
    for stage in plan.stages:
        for delta in stage.deltas:
            current = totals.get(delta.tooth.value)
            if current is None:
                totals[delta.tooth.value] = delta
            else:
                totals[delta.tooth.value] = ToothDelta(
                    tooth=delta.tooth,
                    translate_x_mm=current.translate_x_mm + delta.translate_x_mm,
                    translate_y_mm=current.translate_y_mm + delta.translate_y_mm,
                    translate_z_mm=current.translate_z_mm + delta.translate_z_mm,
                    rotate_tip_deg=current.rotate_tip_deg + delta.rotate_tip_deg,
                    rotate_torque_deg=current.rotate_torque_deg + delta.rotate_torque_deg,
                    rotate_rotation_deg=current.rotate_rotation_deg + delta.rotate_rotation_deg,
                    coordinate_frame=delta.coordinate_frame,
                    source=delta.source,
                    mesh_asset_id=delta.mesh_asset_id,
                )
    return totals


def _steps_for_delta(plan: TreatmentPlan, delta: ToothDelta) -> int:
    caps = plan.settings.movement_caps.caps_for(delta.tooth.value)
    ratios = [
        hypot(delta.translate_x_mm, delta.translate_y_mm) / caps.linear_mm,
        abs(delta.translate_z_mm) / caps.intrusion_extrusion_mm,
        abs(delta.rotate_tip_deg) / caps.angular_deg,
        abs(delta.rotate_torque_deg) / caps.angular_deg,
        abs(delta.rotate_rotation_deg) / caps.rotation_deg,
    ]
    return max(1, ceil(max(ratios)))


def _split_delta(delta: ToothDelta, steps: int) -> ToothDelta:
    return ToothDelta(
        tooth=delta.tooth,
        translate_x_mm=delta.translate_x_mm / steps,
        translate_y_mm=delta.translate_y_mm / steps,
        translate_z_mm=delta.translate_z_mm / steps,
        rotate_tip_deg=delta.rotate_tip_deg / steps,
        rotate_torque_deg=delta.rotate_torque_deg / steps,
        rotate_rotation_deg=delta.rotate_rotation_deg / steps,
        coordinate_frame=delta.coordinate_frame,
        source="manual",
        mesh_asset_id=delta.mesh_asset_id,
    )


def _blocked_axes(plan: TreatmentPlan, tooth_value: str) -> set[MovementAxis]:
    axes: set[MovementAxis] = set()
    for exclusion in plan.movement_exclusions:
        if exclusion.tooth.value == tooth_value:
            axes.update(exclusion.axes)
    return axes
