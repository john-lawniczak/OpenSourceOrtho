"""Serializable evidence state, deliberately without an overall readiness verdict."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReadinessState = Literal["present", "missing", "needs_review", "blocked", "not_assessed"]
ReadinessAction = Literal[
    "upload_scans", "confirm_units", "label_arch", "review_segmentation",
    "review_bite", "attach_cbct", "review_registration", "review_anatomy",
    "review_plan", "configure_export",
]


class ReadinessItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    state: ReadinessState
    detail: str
    scope: Literal["surface", "bite", "root_bone"]
    action: ReadinessAction | None = None
    asset_id: str | None = None


class PlanCheckState(BaseModel):
    status: Literal["no_stages", "limited", "findings_to_review", "checks_completed"]
    warning_count: int = Field(ge=0)
    detail: str


class ArtifactState(BaseModel):
    status: Literal["blocked", "prerequisites_met"]
    blockers: list[str] = Field(default_factory=list)
    geometry_qa: Literal["not_run"] = "not_run"
    detail: str = "Package prerequisites only; geometry QA runs during export."


class IntakeReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    records: list[ReadinessItem]
    plan_consistency: PlanCheckState
    artifacts: ArtifactState
    physical_validation: Literal["not_assessed"] = "not_assessed"
    caveat: str = (
        "Describes the evaluated plan's recorded evidence. Local file availability, "
        "scan orientation, and physical validation are not established by this report. "
        "CBCT is optional for surface review."
    )
