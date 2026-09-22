from __future__ import annotations

from types import SimpleNamespace

import pytest

from orthoplan.dicom_intake import (
    DicomUnavailableError,
    dicom_available,
    parse_dicom_metadata,
    parse_dicom_metadata_safe,
)
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.dicom import extract_dicom_metadata
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import CbctStatus, cbct_handoff, cbct_status


def _fake_dataset() -> SimpleNamespace:
    # A pydicom-like dataset (attribute access) carrying both structural fields
    # and identifiers. extract_dicom_metadata must keep the former, drop the latter.
    return SimpleNamespace(
        Modality="CT",
        StudyDate="20260101",
        PixelSpacing=[0.3, 0.3],
        SliceThickness=0.3,
        Rows=512,
        Columns=512,
        NumberOfFrames=400,
        ImageOrientationPatient=[1, 0, 0, 0, 1, 0],
        PatientName="DOE^JANE",
        PatientID="MRN-12345",
        PatientBirthDate="19900101",
    )


def test_extract_keeps_structural_metadata_and_drops_phi() -> None:
    meta = extract_dicom_metadata(_fake_dataset())
    assert meta.modality == "CT"
    assert meta.study_date == "20260101"
    assert meta.voxel_spacing_mm == (0.3, 0.3, 0.3)
    assert meta.dimensions == (512, 512, 400)
    assert meta.orientation == (1, 0, 0, 0, 1, 0)
    # No PHI must appear anywhere in the serialized metadata.
    dumped = meta.model_dump_json()
    assert "DOE" not in dumped and "JANE" not in dumped
    assert "MRN-12345" not in dumped and "19900101" not in dumped
    # But the redaction is recorded as a note.
    assert any("identifier" in note for note in meta.notes)


def test_extract_handles_missing_fields() -> None:
    meta = extract_dicom_metadata(SimpleNamespace(Modality="MR"))
    assert meta.modality == "MR"
    assert meta.voxel_spacing_mm is None
    assert meta.dimensions is None
    assert meta.orientation is None


@pytest.mark.skipif(dicom_available(), reason="pydicom is installed; tests the fail-closed path")
def test_parse_fails_closed_without_pydicom(tmp_path) -> None:
    src = tmp_path / "scan.dcm"
    src.write_bytes(b"not a real dicom")
    with pytest.raises(DicomUnavailableError):
        parse_dicom_metadata(src)
    meta, error = parse_dicom_metadata_safe(src)
    assert meta is None
    assert error and "dicom" in error.lower()


def _scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id="s", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )


def test_cbct_status_unavailable_then_attached() -> None:
    bare = TreatmentPlan(id="p", scans=[_scan()])
    assert cbct_status(bare) is CbctStatus.UNAVAILABLE

    attached = TreatmentPlan(
        id="p",
        scans=[_scan()],
        case_records=[CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")],
    )
    assert cbct_status(attached) is CbctStatus.ATTACHED


def test_cbct_handoff_points_at_local_viewer_with_references() -> None:
    plan = TreatmentPlan(
        id="p",
        case_records=[CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")],
    )
    handoff = cbct_handoff(plan)
    assert handoff.available is True
    assert "Slicer" in handoff.viewer_suggestion
    assert handoff.local_references == ["records/cb.dcm"]


def test_cbct_attachment_does_not_change_movement_generation() -> None:
    # Safety invariant: attaching a CBCT record must NOT alter movement output
    # until registration and reviewed anatomy exist.
    from orthoplan.api import evaluate_plan
    from orthoplan.model.plan import Stage, ToothDelta, ToothId

    def _plan(records):
        return TreatmentPlan(
            id="p",
            scans=[_scan()],
            case_records=records,
            stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
        )

    without = evaluate_plan(_plan([]))
    with_cbct = evaluate_plan(
        _plan([CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")])
    )
    assert without["frames"] == with_cbct["frames"]
    assert without["optimized_staging"]["plan"]["stages"] == with_cbct["optimized_staging"]["plan"]["stages"]
