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

from orthoplan.evaluation.acquisition import acquisition_advice
from orthoplan.evaluation.engine import run_rules
from orthoplan.model.gaps import data_gap_actions, data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.timeline import project_timeline
from orthoplan.viz.progress import build_stage_progress_frames


def _format_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(plan)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def evaluate_plan(plan: TreatmentPlan) -> dict[str, Any]:
    """Evaluate a validated plan with the canonical engine."""

    findings = run_rules(plan)
    frames = build_stage_progress_frames(plan)
    timeline = project_timeline(plan)
    return {
        "ok": True,
        "scale_confirmed": plan.scale_confirmed,
        "data_gaps": data_gaps(plan),
        "data_gap_actions": [action.model_dump() for action in data_gap_actions(plan)],
        "acquisition_advice": acquisition_advice(plan).model_dump(),
        "findings": [finding.model_dump() for finding in findings],
        "timeline": timeline.model_dump(),
        "frames": [frame.ui_dict() for frame in frames],
        # Approximate per-tooth frames (keyed by FDI value) for a 3D viewer to
        # orient rotation. Empty unless segmentation supplied local frames.
        "tooth_frames": {
            link.tooth.value: link.local_frame.model_dump()
            for link in plan.tooth_meshes
            if link.local_frame is not None
        },
    }


def evaluate_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw plan payload and evaluate it. Never raises."""

    try:
        plan = TreatmentPlan.model_validate(payload)
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}
    return evaluate_plan(plan)
