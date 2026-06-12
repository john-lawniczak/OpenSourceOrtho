from __future__ import annotations

from math import ceil, hypot

from pydantic import BaseModel, Field

from orthoplan.clinical_control_checks import delta_violates_controls, max_control_stage_end
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan


class OptimizerIssue(BaseModel):
    tooth: str
    message: str


class OptimizedStagingResult(BaseModel):
    plan: TreatmentPlan
    issues: list[OptimizerIssue] = Field(default_factory=list)
    caveat: str = (
        "Deterministic staging splits authored movement into configured cap-sized increments. "
        "It is not a biological outcome model, not a complete treatment plan, and does not "
        "authorize physical use. Any physical use is the user's own responsibility and risk."
    )


def optimize_staging(plan: TreatmentPlan) -> OptimizedStagingResult:
    """Return a cap-respecting staged copy of the plan where possible."""

    totals = _target_totals(plan)
    issues: list[OptimizerIssue] = []
    per_tooth_steps: dict[str, int] = {}
    allowed_totals: dict[str, ToothDelta] = {}

    for tooth_value, delta in totals.items():
        steps = _steps_for_delta(plan, delta)
        available = _allowed_stage_indexes(plan, delta, steps)
        if len(available) < steps:
            issues.append(
                OptimizerIssue(
                    tooth=tooth_value,
                    message="Movement omitted because fixed-tooth or movement-exclusion controls apply.",
                )
            )
            continue
        allowed_totals[tooth_value] = delta
        per_tooth_steps[tooth_value] = steps

    if not per_tooth_steps:
        return OptimizedStagingResult(plan=plan.model_copy(update={"stages": []}), issues=issues)

    emitted_counts = {tooth: 0 for tooth in allowed_totals}
    stage_count = _stage_search_limit(plan, per_tooth_steps)
    stages: list[Stage] = []
    for stage_index in range(stage_count):
        deltas = []
        for tooth_value, total in sorted(allowed_totals.items()):
            steps = per_tooth_steps[tooth_value]
            if emitted_counts[tooth_value] >= steps:
                continue
            step_delta = _split_delta(total, steps)
            if delta_violates_controls(plan, step_delta, stage_index):
                continue
            deltas.append(step_delta)
            emitted_counts[tooth_value] += 1
        if deltas or any(emitted_counts[tooth] < per_tooth_steps[tooth] for tooth in allowed_totals):
            stages.append(Stage(index=stage_index, deltas=deltas))
        if all(emitted_counts[tooth] >= per_tooth_steps[tooth] for tooth in allowed_totals):
            break

    return OptimizedStagingResult(plan=plan.model_copy(update={"stages": stages}), issues=issues)


def _allowed_stage_indexes(plan: TreatmentPlan, delta: ToothDelta, steps: int) -> list[int]:
    limit = _stage_search_limit(plan, {delta.tooth.value: steps})
    return [
        index
        for index in range(limit)
        if not delta_violates_controls(plan, _split_delta(delta, steps), index)
    ]


def _stage_search_limit(plan: TreatmentPlan, per_tooth_steps: dict[str, int]) -> int:
    steps = max(per_tooth_steps.values(), default=0)
    finite_control_end = max_control_stage_end(plan)
    return max(steps, finite_control_end + 1) + steps


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
