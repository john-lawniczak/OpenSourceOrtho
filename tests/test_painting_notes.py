"""Notes indexes expose latest source-bound saves, not scan payloads or paths."""
from pathlib import Path

from orthoplan.painting_notes import painting_notes_payload
from orthoplan.region_corrections import save_baseline_corrections
from test_region_corrections import record


def test_notes_index_latest_versions_and_partial_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    assert painting_notes_payload() == {"ok": True, "entries": [], "errors": []}
    for note in ["Old", "Latest <script> is plain text"]:
        saved = save_baseline_corrections({"arch": "lower", "visit": "progress-02",
            "corrections": record("lower", visit="progress-02"), "notes": note})
        assert saved["ok"]
    other = save_baseline_corrections({"arch": "upper", "corrections": record("upper"), "notes": "Baseline"})
    payload = painting_notes_payload()
    assert len(payload["entries"]) == 2
    entry = payload["entries"][-1]
    assert entry["notes"] == "Latest <script> is plain text"
    assert entry["href"] == "./region-review.html?baseline=lower&visit=progress-02"
    assert not {"path", "corrections", "labels_base64"}.intersection(entry)
    Path(other["path"]).write_text("broken JSON")
    partial = painting_notes_payload()
    assert not partial["ok"] and partial["entries"] == [entry]
    assert "Week 1 · Upper" in partial["errors"][0]


def test_cleaned_upper_notes_reopen_matching_version(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    assert save_baseline_corrections({"arch": "upper", "visit": "progress-02", "capture": "upper-clean",
        "corrections": record("upper", visit="progress-02", capture="upper-clean"), "notes": "Check model gaps"})["ok"]
    payload = painting_notes_payload()
    assert payload["ok"] and len(payload["entries"]) == 1
    entry = payload["entries"][0]
    assert entry["title"] == "USER_ONE · Week 18 · Upper · Cleaned version"
    assert entry["href"].endswith("baseline=upper&visit=progress-02&capture=upper-clean")
