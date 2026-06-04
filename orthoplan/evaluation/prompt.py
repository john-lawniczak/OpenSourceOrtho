from __future__ import annotations

import json

from orthoplan.evaluation.providers.base import ModelRequest
from orthoplan.model import DataAvailability
from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan

BOUNDARY_PROMPT = """You are an advisory reviewer for OpenSource Ortho.

You must not approve, clear, diagnose, or determine safety.
You may only provide observational, conditional findings under the supplied data limitations.
Do not invent thresholds. Reference configured caps or cited literature only.
Warnings must include a data gap and a follow-up question.
"""

# Output contract injected into the system prompt. The schema, lint gate, and
# the model's instructions all agree: no verdict language, no mechanics, and
# warnings must carry a data gap and a follow-up question.
ADVISORY_FORMAT = """Respond with ONLY a JSON object of this exact shape:

{"findings": [
  {"severity": "info|notice|warning",
   "category": "data_gap|education|clinician_question",
   "title": "short title",
   "message": "observational, conditional statement",
   "data_gap": "what relevant data is missing (required for warnings)",
   "clinician_question": "a follow-up question (required for warnings)"}
]}

Rules:
- Do NOT use the category "mechanics"; deterministic rules own movement/cap mechanics.
- Do NOT use verdict words (safe, approved, cleared, acceptable, suitable, healthy, good candidate).
- Every "warning" MUST include both "data_gap" and "clinician_question".
- Stay observational and conditional. If you have nothing to add, return {"findings": []}.
"""


def build_boundary_prompt(data: DataAvailability) -> str:
    return f"{BOUNDARY_PROMPT}\nData availability:\n{data.model_dump_json(indent=2)}"


def build_advisory_request(plan: TreatmentPlan) -> ModelRequest:
    """Build a provider-neutral request that injects the safety boundary, the
    declared data availability, the configured caps, and the output schema."""

    context = {
        "data_availability": plan.data.model_dump(),
        "movement_caps": plan.settings.movement_caps.model_dump(),
        "data_gaps": data_gaps(plan),
        "stage_count": len(plan.stages),
        "numbering_system": plan.numbering_system,
    }
    prompt = (
        "Plan context (JSON):\n"
        + json.dumps(context, indent=2)
        + "\n\nReturn ONLY the advisory JSON described in the system message."
    )
    return ModelRequest(
        system=f"{BOUNDARY_PROMPT}\n{ADVISORY_FORMAT}",
        prompt=prompt,
        metadata={"plan_id": plan.id},
    )
