"""Local CBCT/DICOM metadata intake.

Reads ONLY structural study metadata (modality, voxel spacing, dimensions,
orientation, study date) from a local DICOM file using the optional ``pydicom``
dependency. Pixel/volume bytes are never loaded into the plan; they stay in the
local case/record workspace. When ``pydicom`` is not installed, intake fails
closed - it returns an error rather than guessing.
"""

from __future__ import annotations

from pathlib import Path

from orthoplan.model.dicom import DicomMetadata, extract_dicom_metadata


class DicomUnavailableError(RuntimeError):
    """Raised when DICOM parsing is requested but the optional extra is missing."""


def dicom_available() -> bool:
    try:
        import pydicom  # noqa: F401
    except ImportError:
        return False
    return True


def parse_dicom_metadata(path: str | Path) -> DicomMetadata:
    """Parse redacted study metadata from a local DICOM file.

    Raises ``DicomUnavailableError`` if ``pydicom`` is not installed and
    ``ValueError`` if the file cannot be read as DICOM.
    """

    try:
        import pydicom
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise DicomUnavailableError(
            "DICOM parsing requires the optional 'dicom' extra (pip install opensource-ortho[dicom])"
        ) from exc

    try:
        # stop_before_pixels: we never need the volume bytes for metadata.
        dataset = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    except Exception as exc:  # noqa: BLE001 - surface as a value error to callers
        raise ValueError(f"could not read DICOM metadata: {exc}") from exc
    return extract_dicom_metadata(dataset)


def parse_dicom_metadata_safe(path: str | Path) -> tuple[DicomMetadata | None, str | None]:
    """Non-raising variant: returns (metadata, error). One of them is None."""

    try:
        return parse_dicom_metadata(path), None
    except (DicomUnavailableError, ValueError) as exc:
        return None, str(exc)
