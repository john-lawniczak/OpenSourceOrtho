"""Deterministic educational responses when no external provider is selected."""
import re
from typing import Any


def _tooth_size_answer(message: str, context: dict[str, Any]) -> str | None:
    """Recognize a bounded topic; never infer dimensions from label counts."""
    size = re.search(r"\b(bigger|larger|smaller|wider|narrower|longer|shorter|size|width|height|symmetry|asymmetry)\b", message, re.I)
    reshape = re.search(r"\b(fil(?:e|ed|ing)|fied|shav(?:e|ed|ing)|reshap\w*|contour\w*|enameloplasty|ipr)\b", message, re.I)
    teeth = list(dict.fromkeys(re.findall(r"\b[1-4][1-8]\b", message)))
    dental = teeth or re.search(r"\b(tooth|teeth|canine|incisor|crown|enamel)\b", message, re.I)
    if not dental or not (size or reshape):
        return None
    subject = f"teeth {' and '.join(teeth)}" if teeth else "these teeth"
    parts = [f"I can't establish the actual size of {subject} from this chat context."]
    if {"23", "13"}.issubset(teeth):
        parts.append("Using the app's FDI numbering, 23 is the upper left canine and 13 is the upper right canine.")
    if context.get("selected_case"):
        parts.append("USER_ONE's scan inventory and saved label summaries are available, but no measured crown widths or heights are supplied here. Label face counts are not tooth sizes.")
    else:
        parts.append("This request uses the current planning workspace. If you mean USER_ONE, select USER_ONE in Context to include its saved records; that still does not supply measured crown sizes.")
    parts.append("A tooth can look larger because of its angle, visible crown height, or the viewing angle. Compare width and height separately on the same scan, with checked tooth boundaries and scale.")
    if reshape:
        parts.append("Looking bigger alone does not establish a reason to file it down. Enamel removal is irreversible; a dentist would need to assess the actual dimensions, enamel and bite before discussing reshaping. Don't file it yourself.")
    parts.append("Do you mean wider across the crown, longer at the tip, or more prominent?")
    parts.append("This is a built-in offline explanation. Choose a model in Model API Key for a conversational answer using the selected records.")
    return "\n\n".join(parts)


def local_answer(message: str, context: dict[str, Any]) -> str:
    if answer := _tooth_size_answer(message, context):
        return answer
    if case := context.get("selected_case"):
        saved = [f"week {a['week']} {a['arch']}"
                 for a in [*case["saved_baseline_labels"], *case.get("saved_progress_labels", [])] if a.get("saved")]
        return (f"USER_ONE has {len(case['scans'])} scan records in this context. "
                f"Saved labels: {', '.join(saved) or 'none'}. "
                "These are metadata and label summaries; I have not inspected the crown surfaces. "
                "This offline helper provides built-in summaries, not AI reasoning. "
                "Choose a model in Model API Key for a conversational explanation of these records.")
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
    return (
        f"This offline helper provides built-in summaries, not AI reasoning. You are in {ui_label}, "
        f"which is used to {ui_purpose}. This plan has {stage_count} "
        f"stage(s)"
        + (f" and projects to about {duration} week(s)" if duration is not None else "")
        + f". The first deterministic signal is: {first_finding}. The first data limitation is: "
        f"{first_gap}. For a conversational answer to your question, choose a model in "
        f"Model API Key and confirm the selected Context.{thread_note}"
    )
