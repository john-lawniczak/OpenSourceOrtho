"""One rejected companion record must not hide independent consented records."""
import hashlib
import json

import pytest
from orthoplan import personal_model_records as records
from test_personal_model_records import bundle, impression  # noqa: F401


def reindex(root):
    path = root / "record-assets.json"
    data = json.loads(path.read_text())
    data["assets"]["summary.json"] = hashlib.sha256((root / "summary.json").read_bytes()).hexdigest()
    path.write_text(json.dumps(data))


@pytest.mark.parametrize("failure", ["index-json", "summary-json", "missing-fields", "null-review", "lint"])
def test_bad_upper_record_does_not_hide_casts(bundle, impression, failure):  # noqa: F811
    if failure == "index-json":
        (impression / "record-assets.json").write_text("{")
    else:
        summary = json.loads((impression / "summary.json").read_text())
        if failure == "missing-fields":
            del summary["label"]
        if failure == "null-review":
            summary["acquisition_review"] = None
        if failure == "lint":
            summary["findings"] = [{"severity": "notice", "category": "data_gap", "provenance": "MODEL",
                                    "title": "Invalid", "message": "This scan is safe."}]
        (impression / "summary.json").write_text("{" if failure == "summary-json" else json.dumps(summary))
        reindex(impression)
    result = records.personal_model_payload()
    assert result["available"]
    assert not result["impressions"]
    assert result["issues"][0]["bundle"] == "impressions/"
    assert "safe" not in json.dumps(result)


def test_bad_cast_index_preserves_impressions(bundle, impression):  # noqa: F811
    (bundle / "record-assets.json").write_text("{")
    result = records.personal_model_payload()
    assert not result["available"]
    assert result["impressions"][0]["label"] == "Upper impression 1"
    assert result["issues"][0]["bundle"] == "casts"


def test_bad_photo_metadata_preserves_scan(impression):  # noqa: F811
    path = impression / "summary.json"
    summary = json.loads(path.read_text())
    summary["photos"] = [{"label": "missing filename"}]
    path.write_text(json.dumps(summary))
    reindex(impression)
    result = records.personal_model_payload()
    assert result["impressions"][0]["label"] == "Upper impression 1"
    assert result["impressions"][0]["photos"] == []
    assert result["issues"]


def test_rejected_upper_keeps_lower_and_casts(bundle, impression):  # noqa: F811
    lower = impression / "lower"
    lower.mkdir()
    summary = json.loads((impression / "summary.json").read_text())
    summary["label"] = "Lower impression 1"
    (lower / "summary.json").write_text(json.dumps(summary))
    index = json.loads((impression / "record-assets.json").read_text())
    index["assets"] = {"summary.json": hashlib.sha256((lower / "summary.json").read_bytes()).hexdigest()}
    (lower / "record-assets.json").write_text(json.dumps(index))
    consent_path = impression.parents[2] / "consent.json"
    consent = json.loads(consent_path.read_text())
    consent["public_assets"] += [f"{records.IMPRESSION_BUNDLE}/lower/{p.name}" for p in lower.iterdir()]
    consent_path.write_text(json.dumps(consent))
    (impression / "record-assets.json").write_text("{")
    result = records.personal_model_payload()
    assert result["available"]
    assert [r["label"] for r in result["impressions"]] == ["Lower impression 1"]
    assert result["issues"][0]["bundle"] == "impressions/"
