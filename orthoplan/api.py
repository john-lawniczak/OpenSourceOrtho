"""Pure evaluation API shared by the CLI, the HTTP server, and tests.

This is the single place the UI (or any client) obtains findings, data gaps,
the timeline projection, and progress frames. It exists so the browser UI does
NOT reimplement the engine: the Python model is the only source of truth.

``evaluate_plan_payload`` is pure (dict in, dict out) and never raises on
invalid input - validation errors are returned as data so callers can surface
them instead of crashing.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from orthoplan.evaluation.engine import run_rules
from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.timeline import project_timeline
from orthoplan.viz.progress import StageProgressFrame, build_stage_progress_frames


def _format_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(plan)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def _frame_dict(frame: StageProgressFrame) -> dict[str, Any]:
    return {
        "stage_index": frame.stage_index,
        "coordinate_frame": frame.coordinate_frame,
        "rotation_renderable": frame.rotation_renderable,
        "poses": [
            {
                "tooth": pose.tooth.value,
                "translate_x_mm": pose.translate_x_mm,
                "translate_y_mm": pose.translate_y_mm,
                "translate_z_mm": pose.translate_z_mm,
                "rotate_tip_deg": pose.rotate_tip_deg,
                "rotate_torque_deg": pose.rotate_torque_deg,
                "rotate_rotation_deg": pose.rotate_rotation_deg,
                "rotation_renderable": pose.rotation_renderable,
                "pivot": pose.pivot,
            }
            for pose in frame.poses
        ],
    }


def evaluate_plan(plan: TreatmentPlan) -> dict[str, Any]:
    """Evaluate a validated plan with the canonical engine."""

    findings = run_rules(plan)
    frames = build_stage_progress_frames(plan)
    timeline = project_timeline(plan)
    return {
        "ok": True,
        "scale_confirmed": plan.scale_confirmed,
        "data_gaps": data_gaps(plan),
        "findings": [finding.model_dump() for finding in findings],
        "timeline": timeline.model_dump(),
        "frames": [_frame_dict(frame) for frame in frames],
    }


def evaluate_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw plan payload and evaluate it. Never raises."""

    try:
        plan = TreatmentPlan.model_validate(payload)
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}
    return evaluate_plan(plan)
