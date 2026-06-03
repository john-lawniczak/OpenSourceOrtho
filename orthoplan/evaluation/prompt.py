from __future__ import annotations

from orthoplan.model import DataAvailability


BOUNDARY_PROMPT = """You are an advisory reviewer for OpenSource Ortho.

You must not approve, clear, diagnose, or determine clinical safety.
You may only provide observational, conditional findings under the supplied data limitations.
Do not invent thresholds. Reference configured caps or cited literature only.
Warnings must include a data gap and a clinician-facing question.
"""


def build_boundary_prompt(data: DataAvailability) -> str:
    return f"{BOUNDARY_PROMPT}\nData availability:\n{data.model_dump_json(indent=2)}"

