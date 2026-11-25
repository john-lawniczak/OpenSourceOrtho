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


def test_nested_capture_findings_are_linted_before_display_and_download(bundle):
    path = bundle / "summary.json"
    summary = json.loads(path.read_text())
    summary["acquisition_review"] = {"records": [{"findings": [
        {"severity": "notice", "category": "data_gap", "provenance": "MODEL",
         "title": "Invalid capture conclusion", "message": "This tray is safe."}]}]}
    path.write_text(json.dumps(summary))
    index_bundle(bundle)
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_payload()
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_asset(records.ASSET_PREFIX + "summary.json")


def test_comparison_export_lints_nested_provenance_findings(bundle):
    report = {"acquisition_review": {"records": [{"findings": [
        {"severity": "notice", "category": "data_gap", "provenance": "MODEL",
         "title": "Invalid conclusion", "message": "This appliance is safe."}]}]}}
    path = bundle / "dental-comparison.json"
    path.write_text(json.dumps(report))
    consent_path = bundle.parents[2] / "consent.json"
    consent = json.loads(consent_path.read_text())
    consent["public_assets"].append(f"{records.BUNDLE_RELATIVE}/{path.name}")
    consent_path.write_text(json.dumps(consent))
    index_path = bundle / "record-assets.json"
    index = json.loads(index_path.read_text())
    index["assets"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_asset(records.ASSET_PREFIX + path.name)


@pytest.fixture
def impression(bundle):
    root = bundle.parents[2] / records.IMPRESSION_BUNDLE
    root.mkdir()
    summary = {"reported_week": 21, "label": "Upper impression 1", "score": 7.5,
               "score_scope": "subjective exploratory usability", "capture_date": "2026-11-24",
               "impression_date": "2026-11-23", "captures": [], "findings": [],
               "acquisition_review": {"records": [], "repeat_groups": []}}
    (root / "summary.json").write_text(json.dumps(summary))
    (root / "upper-impression-1.stl").write_bytes(b"synthetic negative impression")
    index = {"specimen_id": SAMPLE_SPECIMEN_ID, "progress_record_id": "progress-03",
             "assets": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                        for name in ["summary.json", "upper-impression-1.stl"]}}
    (root / "record-assets.json").write_text(json.dumps(index))
    path = root.parents[2] / "consent.json"
    consent = json.loads(path.read_text())
    consent["public_assets"] += [f"{records.IMPRESSION_BUNDLE}/{file.name}" for file in root.iterdir()]
    path.write_text(json.dumps(consent))
    return root


def test_impression_remains_a_separate_companion_even_without_casts(bundle, impression):
    payload = records.personal_model_payload()
    assert payload["impressions"][0]["capture_date"] == "2026-11-24"
    assert payload["impressions"][0]["impression_date"] == "2026-11-23"
    (bundle / "summary.json").unlink()
    assert not records.personal_model_payload()["available"]
    assert records.personal_model_payload()["impressions"][0]["reported_week"] == 21
    url = records.ASSET_PREFIX + "impressions/upper-impression-1.stl"
    assert records.personal_model_asset(url).read_bytes() == b"synthetic negative impression"
    (impression / "upper-impression-1.stl").write_bytes(b"modified")
    assert records.personal_model_asset(url) is None


@pytest.mark.parametrize("name", ["summary.json", "record-assets.json", "upper-impression-1.stl"])
def test_impression_individual_consent_is_required(impression, name):
    path = impression.parents[2] / "consent.json"
    consent = json.loads(path.read_text())
    consent["public_assets"].remove(f"{records.IMPRESSION_BUNDLE}/{name}")
    path.write_text(json.dumps(consent))
    assert records.personal_model_asset(records.ASSET_PREFIX + "impressions/" + name) is None


def test_impression_findings_and_namespace_are_checked(impression):
    prefix = records.ASSET_PREFIX + "impressions/"
    for name in ["../summary.json", "impressions/summary.json", "%2e%2e/summary.json"]:
        assert records.personal_model_asset(prefix + name) is None
    path = impression / "summary.json"
    summary = json.loads(path.read_text())
    summary["findings"] = [{"severity": "notice", "category": "data_gap", "provenance": "MODEL",
                            "title": "Invalid conclusion", "message": "This scan is safe."}]
    path.write_text(json.dumps(summary))
    index_path = impression / "record-assets.json"
    index = json.loads(index_path.read_text())
    index["assets"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_payload()
    with pytest.raises(ValueError, match="banned verdict"):
        records.personal_model_asset(prefix + path.name)


def test_lower_namespace_is_independent_hash_bound_and_consent_bound(impression):
    lower = impression / "lower"
    lower.mkdir()
    summary = json.loads((impression / "summary.json").read_text())
    summary["label"] = "Lower impression 1"
    (lower / "summary.json").write_text(json.dumps(summary))
    (lower / "lower-impression-1.stl").write_bytes(b"synthetic lower impression")
    index = {"specimen_id": SAMPLE_SPECIMEN_ID, "progress_record_id": "progress-03",
             "assets": {name: hashlib.sha256((lower / name).read_bytes()).hexdigest()
                        for name in ["summary.json", "lower-impression-1.stl"]}}
    (lower / "record-assets.json").write_text(json.dumps(index))
    consent_path = impression.parents[2] / "consent.json"
    consent = json.loads(consent_path.read_text())
    consent["public_assets"] += [f"{records.IMPRESSION_BUNDLE}/lower/{p.name}" for p in lower.iterdir()]
    # Revoking the upper index does not revoke the explicitly consented lower record.
    consent["public_assets"].remove(f"{records.IMPRESSION_BUNDLE}/record-assets.json")
    consent_path.write_text(json.dumps(consent))
    result, = records.personal_model_payload()["impressions"]
    assert result["label"] == "Lower impression 1"
    assert result["asset_prefix"] == "impressions/lower/"
    prefix = records.ASSET_PREFIX + result["asset_prefix"]
    url = prefix + "lower-impression-1.stl"
    assert records.personal_model_asset(url).read_bytes() == b"synthetic lower impression"
    assert records.personal_model_asset(prefix + "../summary.json") is None
    (lower / "lower-impression-1.stl").write_bytes(b"changed")
    assert records.personal_model_asset(url) is None
    consent["public_assets"].remove(f"{records.IMPRESSION_BUNDLE}/lower/record-assets.json")
    consent_path.write_text(json.dumps(consent))
    assert records.impression_payload() is None


@pytest.mark.parametrize("failure", ["revoked", "changed"])
def test_photo_links_require_individual_consent_and_unchanged_bytes(impression, failure):
    name = "upper-impression-photo.png"
    (impression / name).write_bytes(b"synthetic photo")
    photo = {"filename": name, "label": "Upper impression photograph",
             "sha256": hashlib.sha256((impression / name).read_bytes()).hexdigest(),
             "same_condition_as_scan": True, "confirmed_on": "2026-11-25",
             "private_path": "must not reach API"}
    summary_path = impression / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["photos"] = [photo]
    summary_path.write_text(json.dumps(summary))
    index_path = impression / "record-assets.json"
    index = json.loads(index_path.read_text())
    for filename in [name, "summary.json"]:
        index["assets"][filename] = hashlib.sha256((impression / filename).read_bytes()).hexdigest()
    index_path.write_text(json.dumps(index))
    consent_path = impression.parents[2] / "consent.json"
    consent = json.loads(consent_path.read_text())
    consent["public_assets"].append(f"{records.IMPRESSION_BUNDLE}/{name}")
    consent_path.write_text(json.dumps(consent))
    actual, = records.impression_payload()[0]["photos"]
    assert actual["same_condition_as_scan"] and "private_path" not in actual
    if failure == "revoked":
        consent["public_assets"].remove(f"{records.IMPRESSION_BUNDLE}/{name}")
        consent_path.write_text(json.dumps(consent))
    else:
        (impression / name).write_bytes(b"changed")
    assert records.impression_payload()[0]["photos"] == []
