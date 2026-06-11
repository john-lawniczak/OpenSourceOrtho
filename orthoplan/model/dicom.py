"""CBCT/DICOM study metadata - structural fields only, no PHI.

This model deliberately carries ONLY non-identifying acquisition metadata
(modality, voxel spacing, dimensions, orientation, study date). Patient
identifiers (name, id, birth date, address, accession, referring physician) are
never read into it. Volume pixel bytes are never stored here or in plan JSON;
they remain in the local case/record workspace.

``extract_dicom_metadata`` is pure and operates on any object with DICOM-style
attribute access (e.g. a ``pydicom`` Dataset), so it is testable without the
optional ``pydicom`` dependency installed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Tags we will never copy out of a DICOM file, documented so the redaction
# intent is explicit and reviewable.
PHI_TAGS_EXCLUDED = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientAddress",
    "OtherPatientIDs",
    "AccessionNumber",
    "ReferringPhysicianName",
    "InstitutionName",
    "InstitutionAddress",
)


class DicomMetadata(BaseModel):
    """Redacted DICOM study metadata. No patient identifiers, no pixel bytes."""

    modality: str | None = None
    study_date: str | None = None
    voxel_spacing_mm: tuple[float, float, float] | None = None
    dimensions: tuple[int, int, int] | None = None
    orientation: tuple[float, float, float, float, float, float] | None = None
    redacted: bool = True
    notes: list[str] = Field(default_factory=list)


def _f(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _i(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _voxel_spacing(ds) -> tuple[float, float, float] | None:
    spacing = getattr(ds, "PixelSpacing", None)
    if not spacing or len(spacing) < 2:
        return None
    row, col = _f(spacing[0]), _f(spacing[1])
    thickness = _f(getattr(ds, "SliceThickness", None)) or 0.0
    if row is None or col is None:
        return None
    return (row, col, thickness)


def _dimensions(ds) -> tuple[int, int, int] | None:
    rows, cols = _i(getattr(ds, "Rows", None)), _i(getattr(ds, "Columns", None))
    if rows is None or cols is None:
        return None
    frames = _i(getattr(ds, "NumberOfFrames", None)) or 1
    return (rows, cols, frames)


def _orientation(ds) -> tuple[float, float, float, float, float, float] | None:
    raw = getattr(ds, "ImageOrientationPatient", None)
    if not raw or len(raw) < 6:
        return None
    values = [_f(v) for v in raw[:6]]
    if any(v is None for v in values):
        return None
    return tuple(values)  # type: ignore[return-value]


def extract_dicom_metadata(ds) -> DicomMetadata:
    """Pull only structural, non-identifying metadata from a DICOM dataset."""

    notes: list[str] = []
    leaked = [tag for tag in PHI_TAGS_EXCLUDED if getattr(ds, tag, None)]
    if leaked:
        # We saw identifiers in the source but deliberately did NOT copy them.
        notes.append(f"{len(leaked)} identifier tag(s) present in source were not retained")
    return DicomMetadata(
        modality=getattr(ds, "Modality", None),
        study_date=getattr(ds, "StudyDate", None),
        voxel_spacing_mm=_voxel_spacing(ds),
        dimensions=_dimensions(ds),
        orientation=_orientation(ds),
        notes=notes,
    )
