"""Reproducible clinician/research handoff reports.

Reports are canonical JSON artifacts: they bind the plan payload to the engine
version, evaluated findings, data-gap actions, and content hashes. The
``evaluation_sha256`` is stable for the same plan and engine behavior; the
``report_sha256`` identifies the timestamped artifact. Reports intentionally
include mesh metadata only; mesh bytes remain outside the plan/report contract
unless a future workflow explicitly packages them.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from orthoplan import __version__
from orthoplan.api import evaluate_plan
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.plan import TreatmentPlan


REPORT_SCHEMA_VERSION = "orthoplan-report-v1"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_digest(plan: TreatmentPlan) -> str:
    payload = json.loads(plan_to_json(plan, indent=None))
    return sha256_text(canonical_json(payload))


def build_handoff_report(plan: TreatmentPlan, *, created_at: datetime | None = None) -> dict[str, Any]:
    evaluation = evaluate_plan(plan)
    plan_payload = json.loads(plan_to_json(plan, indent=None))
    report_time = created_at or datetime.now(UTC)
    report = {
        "schema": REPORT_SCHEMA_VERSION,
        "created_at": report_time.isoformat(),
        "engine": {"name": "orthoplan", "version": __version__},
        "plan": {
            "id": plan.id,
            "title": plan.title,
            "sha256": sha256_text(canonical_json(plan_payload)),
        },
        "inputs": {
            "scale_confirmed": plan.scale_confirmed,
            "scan_asset_ids": [scan.asset.id for scan in plan.scans],
            "mesh_asset_ids": sorted(plan.asset_ids),
            "tooth_mesh_count": len(plan.tooth_meshes),
        },
        "evaluation": evaluation,
        "evaluation_sha256": sha256_text(canonical_json(evaluation)),
    }
    report["report_sha256"] = sha256_text(canonical_json(report))
    return report


def report_to_json(report: dict[str, Any], *, indent: int | None = 2) -> str:
    return json.dumps(report, indent=indent, sort_keys=True)
