from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan import __version__
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.plan import TreatmentPlan


class PlanVersion(BaseModel):
    version_id: str
    plan_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = __version__
    note: str | None = None
    snapshot: dict


class CaseRecord(BaseModel):
    case_id: str
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    versions: list[PlanVersion] = Field(default_factory=list)


class CaseStore(BaseModel):
    cases: dict[str, CaseRecord] = Field(default_factory=dict)

    def add_version(self, case_id: str, plan: TreatmentPlan, *, note: str | None = None) -> PlanVersion:
        snapshot = json.loads(plan_to_json(plan, indent=None))
        plan_hash = sha256_text(canonical_json(snapshot))
        case = self.cases.setdefault(case_id, CaseRecord(case_id=case_id, title=plan.title))
        version = PlanVersion(
            version_id=f"v{len(case.versions) + 1:04d}",
            plan_hash=plan_hash,
            note=note,
            snapshot=snapshot,
        )
        case.versions.append(version)
        return version


def read_case_store(path: str | Path) -> CaseStore:
    target = Path(path)
    if not target.exists():
        return CaseStore()
    return CaseStore.model_validate_json(target.read_text(encoding="utf-8"))


def write_case_store(store: CaseStore, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(store.model_dump_json(indent=2), encoding="utf-8")
