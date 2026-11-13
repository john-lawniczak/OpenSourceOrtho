"""Local annotation snapshots bind labels to the exact baseline and arch."""
import base64
import json

import pytest

from orthoplan.region_corrections import baseline_source, load_baseline_corrections, save_baseline_corrections


def record(arch="lower", reviewed=False, visit="initial", capture="original"):
    source = baseline_source(arch, visit, capture)
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


def test_week_eighteen_notes_and_labels_are_separate_and_source_bound(tmp_path):
    for arch in ["upper", "lower"]:
        labels = record(arch, visit="progress-02")
        result = save_baseline_corrections({"arch": arch, "visit": "progress-02", "corrections": labels,
                                           "notes": "Week 18 model chip to inspect"}, root=tmp_path)
        assert result["ok"], result
        assert f"week-18-{arch}" in result["path"]
        restored = load_baseline_corrections(arch, visit="progress-02", root=tmp_path)
        assert restored["notes"] == "Week 18 model chip to inspect"
        assert restored["corrections"] == labels and restored["review_status"] == "draft"
        assert not load_baseline_corrections(arch, visit="progress-01", root=tmp_path)["saved"]
        assert not save_baseline_corrections({"arch": arch, "visit": "progress-01", "corrections": labels}, root=tmp_path)["ok"]


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


@pytest.mark.parametrize("arch", ["upper", "lower"])
def test_week_seven_isolated_from_baseline_and_resumes_versions(tmp_path, arch):
    baseline = save_baseline_corrections({"arch": arch, "corrections": record(arch)}, root=tmp_path)
    payload = {"arch": arch, "visit": "progress-01", "corrections": record(arch, visit="progress-01"),
               "notes": "Week 7 partial boundaries", "base_saved_at": None}
    first = save_baseline_corrections(payload, root=tmp_path)
    assert first["ok"] and first["visit"] == "progress-01"
    assert f"week-7-{arch}" in first["path"]
    assert first["filename"] == f"progress-01-{arch}.stl"
    assert load_baseline_corrections(arch, root=tmp_path)["path"] == baseline["path"]
    restored = load_baseline_corrections(arch, visit="progress-01", root=tmp_path)
    assert restored["corrections"] == payload["corrections"]
    assert restored["notes"] == payload["notes"]
    assert not save_baseline_corrections(payload, root=tmp_path)["ok"]
    newer = save_baseline_corrections({**payload, "base_saved_at": first["saved_at"]}, root=tmp_path)
    assert newer["ok"] and newer["path"] != first["path"]
    assert len(list(tmp_path.rglob("*.json"))) == 3


def test_visit_binding_rejects_wrong_mesh_and_unknown_visit(tmp_path):
    payload = {"arch": "upper", "visit": "progress-01", "corrections": record("upper")}
    assert not save_baseline_corrections(payload, root=tmp_path)["ok"]
    for visit in ["../initial", "progress-03", "", None]:
        assert not save_baseline_corrections({**payload, "visit": visit}, root=tmp_path)["ok"]
        assert not load_baseline_corrections("upper", visit=visit, root=tmp_path)["ok"]
    assert not list(tmp_path.rglob("*.json"))


def test_automatic_seed_stays_unreviewed_and_retains_origin(tmp_path):
    correction = {**record("upper", visit="progress-01"), "provenance": "automatic-draft"}
    payload = {"arch": "upper", "visit": "progress-01", "corrections": correction}
    saved = save_baseline_corrections(payload, root=tmp_path)
    assert saved["ok"] and saved["review_status"] == "draft"
    restored = load_baseline_corrections("upper", visit="progress-01", root=tmp_path)
    assert restored["corrections"]["provenance"] == "automatic-draft"
    rejected = save_baseline_corrections({**payload, "corrections": {**correction, "reviewed": True}}, root=tmp_path)
    assert not rejected["ok"]
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_week_eighteen_capture_saves_are_source_bound_and_isolated(tmp_path):
    saves = {}
    for capture in ["original", "fusion-h-4", "fusion-h-6"]:
        payload = {"arch": "lower", "visit": "progress-02", "capture": capture,
                   "corrections": record(visit="progress-02", capture=capture),
                   "notes": f"Notes for {capture}", "base_saved_at": None}
        saved = save_baseline_corrections(payload, root=tmp_path)
        assert saved["ok"]
        saves[capture] = saved
        assert not save_baseline_corrections(payload, root=tmp_path)["ok"]
    assert len({save["corrections"]["source_sha256"] for save in saves.values()}) == 3
    for capture, saved in saves.items():
        assert load_baseline_corrections("lower", visit="progress-02", capture=capture, root=tmp_path)["path"] == saved["path"]
    wrong = {"arch": "lower", "visit": "progress-02", "capture": "fusion-h-4", "corrections": saves["fusion-h-6"]["corrections"]}
    assert not save_baseline_corrections(wrong, root=tmp_path)["ok"]
    assert len(list(tmp_path.rglob("*.json"))) == 3
    for arch, visit, capture in [("upper", "progress-02", "fusion-h-4"), ("lower", "initial", "fusion-h-4"), ("lower", "progress-02", "../other")]:
        assert not load_baseline_corrections(arch, visit=visit, capture=capture, root=tmp_path)["ok"]


def test_clean_upper_cannot_overwrite_original_painting(tmp_path):
    saved = {}
    for capture in ["original", "upper-clean"]:
        payload = {"arch": "upper", "visit": "progress-02", "capture": capture,
                   "corrections": record("upper", visit="progress-02", capture=capture),
                   "notes": capture}
        saved[capture] = save_baseline_corrections(payload, root=tmp_path)
        assert saved[capture]["ok"]
        assert load_baseline_corrections("upper", visit="progress-02", capture=capture, root=tmp_path)["notes"] == capture
    assert saved["original"]["path"] != saved["upper-clean"]["path"]
    assert not save_baseline_corrections({"arch": "upper", "visit": "progress-02", "capture": "upper-clean",
        "corrections": saved["original"]["corrections"]}, root=tmp_path)["ok"]
    for arch, visit in [("lower", "progress-02"), ("upper", "initial"), ("upper", "progress-01")]:
        assert not load_baseline_corrections(arch, visit=visit, capture="upper-clean", root=tmp_path)["ok"]
    assert len(list(tmp_path.rglob("*.json"))) == 2
