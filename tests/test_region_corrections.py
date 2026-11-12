"""Local annotation snapshots bind labels to the exact baseline and arch."""
import base64
import json

import pytest

from orthoplan.region_corrections import baseline_source, load_baseline_corrections, save_baseline_corrections


def record(arch="lower", reviewed=False):
    source = baseline_source(arch)
    labels = bytes([31 if arch == "lower" else 11]) + bytes(source["face_count"] - 1)
    return {"schema": "ortho-region-corrections-v1", "source_sha256": source["sha256"],
            "arch": arch, "face_count": source["face_count"], "labels_base64": base64.b64encode(labels).decode(),
            "reviewed": reviewed, "provenance": "user-corrected"}


def test_separate_arch_versions_roundtrip_and_keep_history(tmp_path):
    assert load_baseline_corrections("lower", root=tmp_path) == {"ok": True, "saved": False}
    first = save_baseline_corrections({"arch": "lower", "corrections": record(), "notes": "Uncertain front tooth"}, root=tmp_path)
    assert first["ok"] and first["review_status"] == "draft"
    final = save_baseline_corrections({"arch": "lower", "corrections": record(reviewed=True), "notes": "Checked surface labels"}, root=tmp_path)
    upper = save_baseline_corrections({"arch": "upper", "corrections": record("upper")}, root=tmp_path)
    assert upper["ok"] and final["ok"]
    assert len(list(tmp_path.rglob("*.json"))) == 3
    restored = load_baseline_corrections("lower", root=tmp_path)
    assert restored["corrections"] == final["corrections"]
    assert restored["notes"] == "Checked surface labels"
    assert restored["review_status"] == "user-reviewed"
    assert load_baseline_corrections("upper", root=tmp_path)["corrections"]["arch"] == "upper"
    assert json.loads(open(first["path"]).read())["notes"] == "Uncertain front tooth"
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("change", [
    {"source_sha256": "0" * 64}, {"arch": "upper"}, {"face_count": 1},
    {"reviewed": "yes"}, {"labels_base64": "not base64"}, {"extra": "field"},
])
def test_rejects_mismatched_and_malformed_records_without_writes(tmp_path, change):
    response = save_baseline_corrections({"arch": "lower", "corrections": {**record(), **change}}, root=tmp_path)
    assert response["ok"] is False
    assert not list(tmp_path.rglob("*.json"))


def test_rejects_upper_ids_in_lower_and_empty_reviewed_map(tmp_path):
    original = record()
    for labels in [bytes([18]) + bytes(original["face_count"] - 1), bytes(original["face_count"])]:
        invalid = {**original, "labels_base64": base64.b64encode(labels).decode(), "reviewed": True}
        assert not save_baseline_corrections({"arch": "lower", "corrections": invalid}, root=tmp_path)["ok"]
    assert not save_baseline_corrections({"arch": "../other", "corrections": original}, root=tmp_path)["ok"]
    assert not load_baseline_corrections("../other", root=tmp_path)["ok"]


def test_corrupted_latest_snapshot_is_not_silently_replaced(tmp_path):
    saved = save_baseline_corrections({"arch": "lower", "corrections": record()}, root=tmp_path)
    from pathlib import Path
    Path(saved["path"]).write_text("broken JSON")
    assert not load_baseline_corrections("lower", root=tmp_path)["ok"]


def test_stale_browser_draft_cannot_supersede_newer_labels(tmp_path):
    first = save_baseline_corrections({"arch": "upper", "corrections": record("upper"),
                                       "base_saved_at": None}, root=tmp_path)
    newer = save_baseline_corrections({"arch": "upper", "corrections": record("upper"),
                                       "base_saved_at": first["saved_at"]}, root=tmp_path)
    stale = save_baseline_corrections({"arch": "upper", "corrections": record("upper"),
                                       "base_saved_at": first["saved_at"]}, root=tmp_path)
    assert not stale["ok"] and "Reload saved" in stale["errors"][0]
    assert load_baseline_corrections("upper", root=tmp_path)["path"] == newer["path"]
    assert len(list(tmp_path.rglob("*.json"))) == 2
