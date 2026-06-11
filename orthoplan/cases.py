from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan import __version__
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import review_tier


class ScanProvenance(BaseModel):
    asset_id: str
    arch: str | None = None
    units: str
    units_confirmed: bool
    provenance: str
    source: str


class RecordProvenance(BaseModel):
    record_id: str
    kind: str
    modality: str | None = None


class CaseProvenance(BaseModel):
    """Queryable provenance summary persisted alongside each plan version.

    The full plan snapshot already embeds every detail; this is the indexable
    digest so listing cases can show modality/units/arch/file ids and review tier
    without rehydrating snapshots. It carries no mesh bytes and no PHI.
    """

    engine_version: str = __version__
    review_tier: str
    units_confirmed: bool
    scans: list[ScanProvenance] = Field(default_factory=list)
    records: list[RecordProvenance] = Field(default_factory=list)
    mesh_asset_ids: list[str] = Field(default_factory=list)


def summarize_provenance(plan: TreatmentPlan) -> CaseProvenance:
    """Derive the indexable provenance digest from a validated plan."""

    return CaseProvenance(
        review_tier=review_tier(plan).value,
        units_confirmed=plan.scale_confirmed,
        scans=[
            ScanProvenance(
                asset_id=scan.asset.id,
                arch=scan.arch,
                units=scan.asset.units.value,
                units_confirmed=scan.asset.units_confirmed,
                provenance=scan.asset.provenance.value,
                source=scan.source,
            )
            for scan in plan.scans
        ],
        records=[
            RecordProvenance(
                record_id=record.id,
                kind=record.kind,
                modality=record.modality,
            )
            for record in plan.case_records
        ],
        mesh_asset_ids=sorted(plan.asset_ids),
    )


class PlanVersion(BaseModel):
    version_id: str
    plan_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = __version__
    note: str | None = None
    provenance: CaseProvenance | None = None
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
            provenance=summarize_provenance(plan),
            snapshot=snapshot,
        )
        case.versions.append(version)
        return version


def default_case_store() -> Path:
    """Default local case-store path (mirrors the mesh-workspace convention)."""

    return Path.cwd() / ".orthoplan-cases.json"


def read_case_store(path: str | Path) -> CaseStore:
    target = Path(path)
    if not target.exists():
        return CaseStore()
    return CaseStore.model_validate_json(target.read_text(encoding="utf-8"))


def write_case_store(store: CaseStore, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(store.model_dump_json(indent=2), encoding="utf-8")
