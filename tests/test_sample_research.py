"""Input provenance, contributor review invalidation and immutable comparisons."""

import base64
import json

import pytest

from orthoplan.research_store import save_record, read_record, folder
from orthoplan.sample_reviews import tooth_bindings, reviews_for, save_tooth_review
from orthoplan.sample_benchmark import label_agreement


def correction(labels, source="a" * 64):
    return {"source_sha256": source, "labels_base64": base64.b64encode(bytes(labels)).decode()}


def test_review_invalidates_only_changed_region_and_scan(monkeypatch):
    import orthoplan.sample_teeth as sample
    import orthoplan.sample_reviews as reviews

    painted = correction([11, 11, 12, 12, 0])
    monkeypatch.setattr(sample, "sample_annotation", lambda *args: (painted, "local-save"))
    monkeypatch.setattr(
        reviews, "baseline_source", lambda *args: {"sha256": painted["source_sha256"]}
    )
    payload = {
        "arch": "upper",
        "visit": "initial",
        "tooth": "11",
        "source_sha256": painted["source_sha256"],
        "mask_sha256": tooth_bindings(painted)["11"],
        "status": "checked",
        "reviewer": "Contributor",
        "notes": "Boundary checked",
    }
    result = save_tooth_review(payload)
    assert result["ok"]
    assert reviews_for(painted)[1]["11"]["status"] == "checked"
    assert reviews_for(correction([11, 11, 12, 0, 0]))[1]["11"]["status"] == "checked"
    assert not reviews_for(correction([11, 0, 12, 12, 0]))[1]
    assert not reviews_for(correction([11, 11, 12, 12, 0], "b" * 64))[1]
    assert save_tooth_review({**payload, "mask_sha256": "stale"})["ok"] is False
    assert save_tooth_review({**payload, "status": "uncertain"})["ok"]
    assert reviews_for(painted)[1]["11"]["status"] == "uncertain"


def test_immutable_records_and_integrity():
    first = save_record("fits", {"value": 1})
    second = save_record("fits", {"value": 2})
    assert first["id"] != second["id"]
    assert read_record("fits", first["id"])["value"] == 1
    path = folder("fits") / (first["id"] + ".json")
    raw = json.loads(path.read_text())
    raw["record"]["value"] = 3
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="integrity"):
        read_record("fits", first["id"])
    with pytest.raises(ValueError):
        read_record("fits", "../secret")


def test_agreement_counts_identity_errors_and_unknown_context():
    result = label_agreement(bytes([11, 11, 12, 12, 0]), bytes([11, 12, 12, 0, 13]))
    rows = {r["tooth"]: r for r in result["per_tooth"]}
    assert rows["11"]["precision"] == 1
    assert rows["11"]["recall"] == 0.5
    assert rows["12"]["iou"] == pytest.approx(1 / 3)
    assert rows["13"]["recall"] is None
    assert result["same_identity_faces"] == 2
    assert result["unlabeled_reference_predicted_faces"] == 1
    with pytest.raises(ValueError):
        label_agreement(b"\x0b", b"")


def test_fit_status_detects_changed_labels_and_preserves_old_record(monkeypatch):
    import orthoplan.sample_refit as refit

    record = save_record(
        "fits", {"inputs": {"arch": "upper"}, "input_digest": "old", "summary": {"fitted": 1}}
    )
    monkeypatch.setattr(refit, "endpoint_inputs", lambda arch: ({"arch": arch}, [], "old"))
    assert not refit.open_refit(record["id"])["stale"]
    monkeypatch.setattr(refit, "endpoint_inputs", lambda arch: ({"arch": arch}, [], "new"))
    assert refit.refit_status("upper")["versions"][0]["stale"]
    assert refit.open_refit(record["id"])["record"] == record
    assert not refit.refit_payload({"arch": "upper", "input_digest": "old"})["ok"]
