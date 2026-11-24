"""Local cast downloads stay explicitly indexed, hash-bound and linted."""
import hashlib
import json

import pytest

from orthoplan import personal_model_records as records
from orthoplan.datasets import SAMPLE_SPECIMEN_ID


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    case = tmp_path / SAMPLE_SPECIMEN_ID
    original = records.SAMPLE_CASE_DIR
    case.mkdir()
    (case / "manifest.json").write_bytes((original / "manifest.json").read_bytes())
    consent = json.loads((original / "consent.json").read_text())
    consent["public_assets"] = [f"{records.BUNDLE_RELATIVE}/{name}" for name in
                                ["record-assets.json", "summary.json", "upper-1-c1.stl"]]
    (case / "consent.json").write_text(json.dumps(consent))
    monkeypatch.setattr(records, "SAMPLE_CASE_DIR", case)
    root = case / records.BUNDLE_RELATIVE
    root.mkdir(parents=True)
    summary = {"date": "2026-11-23", "models": [], "captures": [], "findings": [],
               "desktop_path": "not part of the API"}
    (root / "summary.json").write_text(json.dumps(summary))
    (root / "upper-1-c1.stl").write_bytes(b"synthetic cast fixture")
    index_bundle(root)
    return root


@pytest.mark.parametrize("name", ["record-assets.json", "summary.json", "upper-1-c1.stl"])
def test_revoked_asset_consent_blocks_download(bundle, name):
    consent_path = bundle.parents[2] / "consent.json"
    consent = json.loads(consent_path.read_text())
    consent["public_assets"].remove(f"{records.BUNDLE_RELATIVE}/{name}")
    consent_path.write_text(json.dumps(consent))
    assert records.personal_model_asset(records.ASSET_PREFIX + name) is None
    if name != "upper-1-c1.stl":
        assert records.personal_model_payload() == {"available": False}


def index_bundle(root):
    (root / "record-assets.json").write_text(json.dumps({
        "specimen_id": SAMPLE_SPECIMEN_ID, "progress_record_id": "progress-03",
        "assets": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   for name in ["summary.json", "upper-1-c1.stl"]}}))


def test_unavailable_public_installation_has_no_companion_records(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "SAMPLE_CASE_DIR", tmp_path)
    assert records.personal_model_payload() == {"available": False}
    assert records.personal_model_asset(records.ASSET_PREFIX + "upper-1-c1.stl") is None


def test_only_indexed_unchanged_bytes_and_summary_fields_are_exposed(bundle):
    payload = records.personal_model_payload()
    assert payload["available"] and payload["reported_week"] == 21
    assert "desktop_path" not in payload
    path = records.personal_model_asset(records.ASSET_PREFIX + "upper-1-c1.stl")
    assert path.read_bytes() == b"synthetic cast fixture"
    (bundle / "unlisted.stl").write_bytes(b"unrelated contribution")
    assert records.personal_model_asset(records.ASSET_PREFIX + "unlisted.stl") is None
    path.write_bytes(b"replaced")
    assert records.personal_model_asset(records.ASSET_PREFIX + path.name) is None


@pytest.mark.parametrize("name", ["../summary.json", "%2e%2e/summary.json", "/summary.json",
                                  "nested/summary.json", "..\\summary.json", "summary.json%00"])
def test_traversal_is_rejected_even_if_in_index(bundle, name):
    index = json.loads((bundle / "record-assets.json").read_text())
    index["assets"][name] = index["assets"]["summary.json"]
    (bundle / "record-assets.json").write_text(json.dumps(index))
    assert records.personal_model_asset(records.ASSET_PREFIX + name) is None


def test_symlinked_file_and_bundle_are_rejected(bundle, tmp_path):
    raw = (bundle / "upper-1-c1.stl").read_bytes()
    target = tmp_path / "outside.stl"
    target.write_bytes(raw)
    (bundle / "upper-1-c1.stl").unlink()
    (bundle / "upper-1-c1.stl").symlink_to(target)
    assert records.personal_model_asset(records.ASSET_PREFIX + "upper-1-c1.stl") is None
    moved = bundle.with_name("moved")
    bundle.rename(moved)
    bundle.symlink_to(moved, target_is_directory=True)
    assert records.personal_model_payload() == {"available": False}


def test_model_verdict_is_rejected_before_summary_display_or_export(bundle):
    summary = json.loads((bundle / "summary.json").read_text())
    summary["findings"] = [{"severity": "notice", "category": "data_gap", "provenance": "MODEL",
                            "title": "Invalid conclusion", "message": "This cast is safe."}]
    (bundle / "summary.json").write_text(json.dumps(summary))
    index_bundle(bundle)
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_payload()
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_asset(records.ASSET_PREFIX + "summary.json")


def test_visit_identity_cannot_be_substituted(bundle):
    path = bundle / "record-assets.json"
    index = json.loads(path.read_text())
    index["progress_record_id"] = "progress-02"
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="identity mismatch"):
        records.personal_model_payload()
