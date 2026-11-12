"""Deterministic educational responses when no external provider is selected."""
from typing import Any


def local_answer(message: str, context: dict[str, Any]) -> str:
    if case := context.get("selected_case"):
        saved = [a["arch"] for a in case["saved_baseline_labels"] if a.get("saved")]
        return (f"USER_ONE has {len(case['scans'])} scan records in this context. "
                f"Saved baseline labels: {', '.join(saved) or 'none'}. "
                "These are metadata and label summaries; I have not inspected the crown surfaces. "
                "Select an external provider for an explanation of these records.")
    findings = context.get("findings") or []
    gaps = context.get("data_gaps") or []
    timeline = context.get("timeline") or {}
    ui_context = context.get("ui_context") or {}
    stage_count = context.get("stage_count", 0)
    duration = timeline.get("projected_duration_weeks")
    first_gap = gaps[0] if gaps else "no declared gap from the current context"
    first_finding = findings[0]["title"] if findings else "no deterministic finding from the current rules"
    ui_label = ui_context.get("label") or "the current workspace stage"
    ui_purpose = ui_context.get("purpose") or "review the plan context"
    history = context.get("history") or []
    previous_user = next(
        (item.get("content") for item in reversed(history) if item.get("role") == "user"),
        None,
    )
    thread_note = f" You previously asked: \"{previous_user}\"." if previous_user else ""
    asked = message.strip()
    return (
        f"I can review the current plan context, but only as education. You are in {ui_label}, "
        f"which is used to {ui_purpose}. This plan has {stage_count} "
        f"stage(s)"
        + (f" and projects to about {duration} week(s)" if duration is not None else "")
        + f". The first deterministic signal is: {first_finding}. The first data limitation is: "
        f"{first_gap}. For your question, \"{asked}\", the most useful next step is to compare the "
        "visual movement timeline with the findings and collect any missing records before relying on "
        f"the preview for clinical decisions.{thread_note}"
    )
