"""Contributed-dataset identity and a privacy-safe manifest.

As contributed scan data scales, each dataset needs a stable, non-identifying
handle so it can be tracked, deduplicated, and referenced without ever embedding
patient identity. This module owns:

- ``new_specimen_id`` - a fresh UUID-backed specimen id (``spec-<uuid4 hex>``)
- ``ContributedScan`` / ``DatasetManifest`` - redacted, no-PHI metadata only

Privacy posture (consistent with ``model/assets.py``):

- Mesh bytes are never stored; only redacted metadata and a relative reference.
- The manifest deliberately has NO name/DOB/contact fields. Identity is a random
  UUID, not anything derived from the patient.
- File references are reduced to a redacted basename.

This module is pure data (no file IO, no provider SDKs). The CLI does the STL
inspection and writes the manifest; see ``orthoplan/cli.py``.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from orthoplan import __version__
from orthoplan.model.assets import (
    ArchName,
    BoundingBox,
    MeshProvenance,
    MeshUnits,
    redact_reference,
)

SPECIMEN_ID_PREFIX = "spec-"

ScanRole = Literal["initial", "progress", "refinement", "final", "unknown"]

_ROLE_ARCH_RE = re.compile(
    r"^(?P<role>initial|progress|refinement|final)"
    r"(?:-(?P<sequence>\d{1,3}))?"
    r"-(?P<arch>upper|lower|maxillary|mandibular|bite|occlusion)\.stl$",
    re.IGNORECASE,
)

# Fields that must never appear in a contributed manifest. Enforced so a future
# edit cannot quietly reintroduce protected health information.
_FORBIDDEN_PHI_FIELDS = frozenset(
    {
        "name",
        "patient_name",
        "first_name",
        "last_name",
        "dob",
        "date_of_birth",
        "birthdate",
        "ssn",
        "mrn",
        "email",
        "phone",
        "address",
    }
)


def new_specimen_id() -> str:
    """Return a fresh, non-identifying specimen id (``spec-<uuid4 hex>``)."""

    return f"{SPECIMEN_ID_PREFIX}{uuid.uuid4().hex}"


def text_has_phi_marker(value: str | None) -> bool:
    """Return True when free text appears to mention forbidden PHI field labels."""

    return bool(value and any(marker in value.lower() for marker in _FORBIDDEN_PHI_FIELDS))


def infer_scan_labels(filename: str) -> tuple[ScanRole, ArchName | None, int | None]:
    """Infer contribution role/arch labels from the standard case-bundle filename.

    The filename convention is the stable public contract for contributed case
    bundles. Unknown labels are allowed so older/simple datasets keep loading, but
    standard filenames unlock longitudinal benchmark grouping.
    """

    name = Path(filename).name
    match = _ROLE_ARCH_RE.match(name)
    if not match:
        return "unknown", None, None
    role = match.group("role").lower()
    arch_label = match.group("arch").lower()
    arch = {
        "upper": "maxillary",
        "maxillary": "maxillary",
        "lower": "mandibular",
        "mandibular": "mandibular",
    }.get(arch_label)
    sequence = match.group("sequence")
    return (
        role,  # type: ignore[return-value]
        arch,  # type: ignore[return-value]
        int(sequence) if sequence else None,
    )


class IPRContactSummary(BaseModel):
    """A non-proprietary, patient-anonymous IPR contact summary."""

    between: tuple[str, str]
    amount_mm: float = Field(ge=0)


class PlanSummary(BaseModel):
    """Small, non-proprietary description of intended treatment controls.

    This is intentionally less detailed than ``TreatmentPlan`` so a general user
    can contribute useful context without copying proprietary planning files.
    """

    model_config = {"extra": "forbid", "populate_by_name": True}

    schema_id: Literal["opensource-ortho-plan-summary-v1"] = Field(
        default="opensource-ortho-plan-summary-v1",
        alias="schema",
    )
    stage_count: int | None = Field(default=None, ge=0)
    wear_interval_days: int | None = Field(default=None, ge=1)
    arches_treated: list[Literal["upper", "lower"]] = Field(default_factory=list)
    moved_teeth: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    ipr_contacts: list[IPRContactSummary] = Field(default_factory=list)
    spacing_contacts: list[IPRContactSummary] = Field(default_factory=list)
    locked_teeth: list[str] = Field(default_factory=list)
    movement_exclusions: list[str] = Field(default_factory=list)
    refinement_count: int | None = Field(default=None, ge=0)
    tracking_notes: str | None = None
    notes: str | None = None

    @field_validator("tracking_notes", "notes")
    @classmethod
    def free_text_has_no_phi_markers(cls, value: str | None) -> str | None:
        if text_has_phi_marker(value):
            raise ValueError(
                "plan summary text must not reference patient-identifying fields "
                f"({', '.join(sorted(_FORBIDDEN_PHI_FIELDS))})"
            )
        return value


class ContributedScan(BaseModel):
    """Redacted, no-PHI metadata for a single contributed scan file."""

    filename: str
    role: ScanRole = "unknown"
    sequence_index: int | None = Field(default=None, ge=1)
    sha256: str
    units: MeshUnits = MeshUnits.UNVERIFIED
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED
    arch: ArchName | None = None
    vertex_count: int = Field(ge=0)
    face_count: int = Field(ge=0)
    bounds: BoundingBox | None = None

    @field_validator("filename")
    @classmethod
    def filename_is_redacted_basename(cls, value: str) -> str:
        # Reduce to a non-identifying basename; directory structure commonly
        # embeds patient names, so it is stripped here as well as on ingest.
        return redact_reference(value)

    @field_validator("role")
    @classmethod
    def final_scans_do_not_have_sequence(cls, value: ScanRole) -> ScanRole:
        return value


class DatasetManifest(BaseModel):
    """A tracked, privacy-safe record of a contributed dataset.

    Identity is a random ``specimen_id`` - never anything derived from a patient.
    ``model_config`` forbids extra fields so a stray ``name``/``dob`` key on an
    inbound payload is rejected rather than silently stored.
    """

    model_config = {"extra": "forbid"}

    specimen_id: str = Field(default_factory=new_specimen_id)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = __version__
    scans: list[ContributedScan] = Field(default_factory=list)
    plan_summary: PlanSummary | None = None
    plan_summary_filename: str | None = None
    outcome_notes_filename: str | None = None
    outcome_notes_sha256: str | None = None
    consent_acknowledged: bool = False
    phi_removed: bool = False
    notes: str | None = None

    @field_validator("specimen_id")
    @classmethod
    def specimen_id_is_prefixed(cls, value: str) -> str:
        if not value.startswith(SPECIMEN_ID_PREFIX):
            raise ValueError(f"specimen_id must start with {SPECIMEN_ID_PREFIX!r}")
        return value

    @field_validator("notes")
    @classmethod
    def notes_have_no_phi_markers(cls, value: str | None) -> str | None:
        if text_has_phi_marker(value):
            raise ValueError(
                "notes must not reference patient-identifying fields "
                f"({', '.join(sorted(_FORBIDDEN_PHI_FIELDS))})"
            )
        return value

    @field_validator("plan_summary_filename", "outcome_notes_filename")
    @classmethod
    def sidecar_filename_is_redacted_basename(cls, value: str | None) -> str | None:
        return redact_reference(value) if value else value


def read_manifest(path: str | Path) -> DatasetManifest:
    target = Path(path)
    return DatasetManifest.model_validate_json(target.read_text(encoding="utf-8"))


def read_plan_summary(path: str | Path) -> PlanSummary:
    target = Path(path)
    return PlanSummary.model_validate_json(target.read_text(encoding="utf-8"))


def write_manifest(manifest: DatasetManifest, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.model_dump_json(indent=2, by_alias=True), encoding="utf-8")


def manifest_to_json(manifest: DatasetManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2)
