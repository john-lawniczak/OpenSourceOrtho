from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from orthoplan.model.assets import BoundingBox, MeshUnits
from orthoplan.model.dataset import (
    SPECIMEN_ID_PREFIX,
    ContributedScan,
    DatasetManifest,
    PlanSummary,
    new_specimen_id,
    infer_scan_labels,
    read_manifest,
    write_manifest,
)


def _scan() -> ContributedScan:
    return ContributedScan(
        filename="scan.stl",
        sha256="a" * 64,
        units=MeshUnits.MM,
        arch="maxillary",
        vertex_count=300,
        face_count=100,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(40, 40, 12)),
    )


def test_new_specimen_id_is_prefixed_and_unique() -> None:
    a = new_specimen_id()
    b = new_specimen_id()
    assert a.startswith(SPECIMEN_ID_PREFIX)
    assert b.startswith(SPECIMEN_ID_PREFIX)
    assert a != b


def test_manifest_round_trips(tmp_path: Path) -> None:
    manifest = DatasetManifest(scans=[_scan()], consent_acknowledged=True, phi_removed=True)
    target = tmp_path / "nested" / "manifest.json"
    write_manifest(manifest, target)
    loaded = read_manifest(target)
    assert loaded.specimen_id == manifest.specimen_id
    assert len(loaded.scans) == 1
    assert loaded.scans[0].sha256 == "a" * 64


def test_contributed_scan_redacts_filename_directory() -> None:
    # A directory path commonly embeds a patient name; only the basename survives.
    scan = ContributedScan(
        filename="/exports/patient_jane_doe/scan.stl",
        sha256="b" * 64,
        vertex_count=3,
        face_count=1,
    )
    assert scan.filename == "scan.stl"


def test_manifest_rejects_extra_phi_fields() -> None:
    # extra="forbid" means a stray patient-identifying key is rejected, not stored.
    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(
            {"scans": [], "patient_name": "Jane Doe"}
        )


def test_manifest_rejects_phi_in_notes() -> None:
    with pytest.raises(ValidationError):
        DatasetManifest(notes="patient DOB 1990-01-01")


def test_specimen_id_must_be_prefixed() -> None:
    with pytest.raises(ValidationError):
        DatasetManifest(specimen_id="12345")


def test_manifest_has_no_phi_fields_by_construction() -> None:
    # Lock the schema: none of these protected fields may exist on the model.
    fields = set(DatasetManifest.model_fields) | set(ContributedScan.model_fields)
    for forbidden in ("name", "patient_name", "dob", "date_of_birth", "email", "mrn", "ssn"):
        assert forbidden not in fields


def test_scan_labels_are_inferred_from_standard_filename() -> None:
    role, arch, sequence = infer_scan_labels("/tmp/spec/progress-02-lower.stl")
    assert role == "progress"
    assert arch == "mandibular"
    assert sequence == 2

    role, arch, sequence = infer_scan_labels("final-upper.stl")
    assert role == "final"
    assert arch == "maxillary"
    assert sequence is None


def test_unknown_scan_filename_stays_loadable() -> None:
    role, arch, sequence = infer_scan_labels("scan.stl")
    assert role == "unknown"
    assert arch is None
    assert sequence is None


def test_plan_summary_accepts_non_proprietary_context() -> None:
    summary = PlanSummary(
        stage_count=24,
        wear_interval_days=7,
        arches_treated=["upper", "lower"],
        moved_teeth=["11", "21"],
        ipr_contacts=[{"between": ["11", "21"], "amount_mm": 0.2}],
        refinement_count=1,
    )
    assert summary.schema_id == "opensource-ortho-plan-summary-v1"
    assert summary.ipr_contacts[0].between == ("11", "21")


def test_plan_summary_rejects_phi_markers() -> None:
    with pytest.raises(ValidationError):
        PlanSummary(notes="Patient email is in the attached file")
