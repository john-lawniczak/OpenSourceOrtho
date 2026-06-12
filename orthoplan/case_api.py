"""Plan-versioning gateway shared by the HTTP server and the CLI.

Wraps the ``cases.py`` primitive (CaseStore/PlanVersion) in pure dict-in/dict-out
functions that never raise - validation and IO failures come back as data so the
UI and CLI can surface them. A "case" groups versions of one plan; the default
``case_id`` is the plan id. Snapshots are the full plan JSON (no mesh bytes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from orthoplan.cases import PlanVersion, read_case_store, write_case_store
from orthoplan.model.plan import TreatmentPlan


def _errors(exc: ValidationError) -> list[str]:
    out: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(p) for p in item.get("loc", ())) or "(plan)"
        out.append(f"{loc}: {item.get('msg', 'invalid')}")
    return out


def _summary(version: PlanVersion) -> dict[str, Any]:
    return {
        "version_id": version.version_id,
        "plan_hash": version.plan_hash,
        "created_at": version.created_at.isoformat(),
        "engine_version": version.engine_version,
        "note": version.note,
        "provenance": version.provenance.model_dump(mode="json") if version.provenance else None,
    }


def save_plan_version_payload(payload: dict[str, Any], *, store_path: str | Path) -> dict[str, Any]:
    """Validate a plan and append it as a new version of its case. Never raises."""

    try:
        plan = TreatmentPlan.model_validate(payload.get("plan"))
    except ValidationError as exc:
        return {"ok": False, "errors": _errors(exc)}

    case_id = str(payload.get("case_id") or plan.id)
    raw_note = payload.get("note")
    note = str(raw_note) if raw_note else None
    try:
        store = read_case_store(store_path)
        version = store.add_version(case_id, plan, note=note)
        write_case_store(store, store_path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": [f"case store write failed: {exc}"]}

    return {
        "ok": True,
        "case_id": case_id,
        "version": _summary(version),
        "versions": [_summary(v) for v in store.cases[case_id].versions],
    }


def list_cases_payload(*, store_path: str | Path) -> dict[str, Any]:
    store = read_case_store(store_path)
    return {
        "ok": True,
        "cases": [
            {
                "case_id": case.case_id,
                "title": case.title,
                "version_count": len(case.versions),
                "created_at": case.created_at.isoformat(),
                "latest": _summary(case.versions[-1]) if case.versions else None,
            }
            for case in store.cases.values()
        ],
    }


def case_versions_payload(case_id: str, *, store_path: str | Path) -> dict[str, Any]:
    """Return a case's versions WITH snapshots so a client can restore directly."""

    store = read_case_store(store_path)
    case = store.cases.get(case_id)
    if case is None:
        return {"ok": False, "errors": [f"unknown case {case_id!r}"]}
    return {
        "ok": True,
        "case_id": case_id,
        "title": case.title,
        "versions": [{**_summary(v), "snapshot": v.snapshot} for v in case.versions],
    }
