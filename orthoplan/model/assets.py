"""Uploaded mesh asset metadata.

Privacy posture (Phase 1):

- Mesh bytes are NEVER stored in serialized plan JSON. Only redacted metadata
  and an optional relative/local reference are kept.
- Absolute paths and parent-directory traversal are rejected, because file paths
  can embed patient names or DOB.
- STL files carry no units; units default to ``UNVERIFIED`` and must be
  confirmed by the user before cap evaluation runs.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from orthoplan.model.dicom import DicomMetadata

ArchName = Literal["maxillary", "mandibular"]
CaseRecordKind = Literal["cbct", "dicom", "photo", "radiograph", "note", "document"]


class MeshUnits(StrEnum):
    UNVERIFIED = "unverified"
    MM = "mm"
    CM = "cm"
    INCH = "inch"
    METER = "meter"


class MeshProvenance(StrEnum):
    PATIENT_DERIVED = "patient-derived"
    IMPORTED = "imported"
    MANUAL = "manual"
    MODEL_GENERATED = "model-generated"
    SYNTHETIC = "synthetic"


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]

    @property
    def size(self) -> tuple[float, float, float]:
        return tuple(hi - lo for lo, hi in zip(self.min_xyz, self.max_xyz))  # type: ignore[return-value]

    @property
    def max_span(self) -> float:
        return max(hi - lo for lo, hi in zip(self.min_xyz, self.max_xyz))


def redact_reference(raw_path: str) -> str:
    """Reduce a path to a non-identifying basename.

    Does not guarantee removal of all identifiers, but strips directory
    structure (which commonly contains patient names) and any drive/anchor.
    """

    return os.path.basename(raw_path.replace("\\", "/").rstrip("/"))


class MeshQualityReport(BaseModel):
    """Observational mesh quality metadata from inspection."""

    inspector: str = "internal-stl"
    watertight: bool | None = None
    winding_consistent: bool | None = None
    degenerate_faces: int | None = None
    notes: list[str] = Field(default_factory=list)


class MeshAsset(BaseModel):
    """Redacted metadata for an uploaded mesh. Bytes are not stored."""

    id: str
    format: str
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED
    units: MeshUnits = MeshUnits.UNVERIFIED
    vertex_count: int = Field(ge=0)
    face_count: int = Field(ge=0)
    bounds: BoundingBox | None = None
    quality: MeshQualityReport | None = None
    sha256: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Optional relative/local reference only. Never absolute, never PHI.
    reference: str | None = None

    @field_validator("reference")
    @classmethod
    def reference_is_relative_and_redacted(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.replace("\\", "/")
        if os.path.isabs(value) or normalized.startswith("/") or ":" in value:
            raise ValueError("asset reference must be relative and contain no absolute path")
        if ".." in normalized.split("/"):
            raise ValueError("asset reference must not traverse parent directories")
        return value

    @property
    def units_confirmed(self) -> bool:
        return self.units != MeshUnits.UNVERIFIED


class UploadedScan(BaseModel):
    asset: MeshAsset
    arch: ArchName | None = None
    source: str = "intraoral-scan"
    notes: str | None = None

    @property
    def units_confirmed(self) -> bool:
        return self.asset.units_confirmed


class CaseRecord(BaseModel):
    """Local-only case context record.

    Binary payloads (DICOM volumes, photos, radiographs, documents) live in the
    local case/record workspace. Plan JSON carries only this redacted metadata and
    a local reference id/path; it never embeds those bytes.
    """

    id: str
    kind: CaseRecordKind
    modality: str | None = None
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None
    local_reference: str | None = None
    note_text: str | None = Field(default=None, max_length=2000)
    provenance: str = "patient-derived"
    # Structural CBCT/DICOM metadata (no PHI, no pixel bytes). Populated only for
    # cbct/dicom records when the optional ``dicom`` extra parses the study.
    dicom: DicomMetadata | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("filename")
    @classmethod
    def filename_is_basename(cls, value: str | None) -> str | None:
        return redact_reference(value) if value else None

    @field_validator("local_reference")
    @classmethod
    def local_reference_is_relative_and_redacted(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.replace("\\", "/")
        if os.path.isabs(value) or normalized.startswith("/") or ":" in value:
            raise ValueError("case record reference must be relative and contain no absolute path")
        if ".." in normalized.split("/"):
            raise ValueError("case record reference must not traverse parent directories")
        return value


def bounding_box_sanity(asset: MeshAsset) -> str | None:
    """Observational scale check. Never infers units; only flags a data gap."""

    if not asset.units_confirmed:
        return "scan units unverified; geometry scale cannot be trusted until confirmed"
    if asset.bounds is None:
        return None
    span = asset.bounds.max_span
    if asset.units == MeshUnits.MM and not (30.0 <= span <= 120.0):
        return (
            f"declared mm geometry spans {span:.1f} mm, outside the typical 30-120 mm "
            "dental-arch range; confirm scale and units"
        )
    return None
