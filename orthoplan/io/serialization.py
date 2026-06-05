"""Lossless JSON serialization for treatment plans.

Round-trips a ``TreatmentPlan`` through JSON so a UI or file store can persist
and reload the exact plan contract. Mesh bytes are never part of the plan, so
serialized plans contain only redacted asset metadata.
"""

from __future__ import annotations

from pathlib import Path

from orthoplan.model.plan import TreatmentPlan


def plan_to_json(plan: TreatmentPlan, *, indent: int | None = 2) -> str:
    return plan.model_dump_json(indent=indent)


def plan_from_json(data: str) -> TreatmentPlan:
    return TreatmentPlan.model_validate_json(data)


def write_plan(plan: TreatmentPlan, path: str | Path) -> None:
    Path(path).write_text(plan_to_json(plan), encoding="utf-8")


def read_plan(path: str | Path) -> TreatmentPlan:
    return plan_from_json(Path(path).read_text(encoding="utf-8"))
