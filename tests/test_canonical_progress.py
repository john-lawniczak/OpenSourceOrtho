"""Integrity and conservative comparison boundaries for the real progress pair."""

import hashlib
import json

from orthoplan.datasets import SAMPLE_CASE_DIR
import struct

from orthoplan.model.dataset import read_manifest
from orthoplan.validation.benchmark_corpus import reviewed_benchmark_corpus
from orthoplan.validation.longitudinal_benchmark import longitudinal_outcome_reports


CASE = SAMPLE_CASE_DIR


def test_progress_assets_match_manifest_and_source_inventory():
    manifest = read_manifest(CASE / "manifest.json")
    source = json.loads((CASE / "progress-01-source-metadata.json").read_text())
    assert source["specimen_id"] == manifest.specimen_id
    progress = [scan for scan in manifest.scans if scan.role == "progress"]
    assert {scan.arch for scan in progress} == {"maxillary", "mandibular"}
    assert len(manifest.scans) == 4
    for scan in progress:
        raw = (CASE / scan.filename).read_bytes()
        assert raw[:80] == b" " * 80
        assert len(raw) == 84 + 50 * scan.face_count
        assert struct.unpack_from("<I", raw, 80)[0] == scan.face_count
        assert hashlib.sha256(raw).hexdigest() == scan.sha256
        assert scan.units == "unverified"
        assert scan.sequence_index == 1
    for item in source["images"]:
        raw = (CASE / item["filename"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert len(raw) == item["size_bytes"]


def test_progress_comparison_does_not_report_unverified_mm_error():
    report = longitudinal_outcome_reports(CASE)[0]
    assert len(report.tracking_errors) == 2
    for metric in report.tracking_errors:
        assert metric.value_mm is None
        assert metric.status == "unverified-or-unsupported-units"
    comparison = json.loads((CASE / "derived/progress-01-comparison.json").read_text())
    assert comparison["registration_status"] == "not-validated"
    assert comparison["per_tooth_movement_mm"] is None
    assert comparison["tracking_error_mm"] is None


def test_new_visits_do_not_inherit_baseline_benchmark_review():
    case = reviewed_benchmark_corpus()[0]
    assert {scan.filename for scan in case.scans} == {
        "initial-upper.stl", "initial-lower.stl",
    }


def test_timeline_preserves_confirmed_progress_and_calendar_days():
    timeline = json.loads((CASE / "longitudinal-record.json").read_text())
    assert timeline["timing"]["reported_week"] == 7
    assert timeline["timing"]["recorded_treatment_start_to_progress_days"] == 30
    assert timeline["timing"]["status"] == "user-confirmed-progress-label"
    assert timeline["timing"]["reported_wear_interval_days"] == 5
    assert timeline["timing"]["wear_interval_start_date"] is None
    assert timeline["comparison"]["final_scan_available"] is False
    context = json.loads((CASE / "treatment-context.json").read_text())
    assert context["reported_progress"]["tray_number"] == 5
    assert context["progress_records"][0]["reported_tray_number"] is None
    assert context["progress_records"][0]["wear_interval_days"] == 5
    assert context["reported_progress"]["wear_interval_days"] is None
    manifest = read_manifest(CASE / "manifest.json")
    assert manifest.plan_summary.wear_interval_days == 5
