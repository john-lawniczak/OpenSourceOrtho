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
from pathlib import Path

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


class ContributedScan(BaseModel):
    """Redacted, no-PHI metadata for a single contributed scan file."""

    filename: str
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
        if value and any(marker in value.lower() for marker in _FORBIDDEN_PHI_FIELDS):
            raise ValueError(
                "notes must not reference patient-identifying fields "
                f"({', '.join(sorted(_FORBIDDEN_PHI_FIELDS))})"
            )
        return value


def read_manifest(path: str | Path) -> DatasetManifest:
    target = Path(path)
    return DatasetManifest.model_validate_json(target.read_text(encoding="utf-8"))


def write_manifest(manifest: DatasetManifest, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def manifest_to_json(manifest: DatasetManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json"), indent=2)
