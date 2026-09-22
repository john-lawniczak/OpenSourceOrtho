"""Both mobile packages must use the same real, hash-bound observed visits."""

import json
from pathlib import Path

from orthoplan.datasets import SAMPLE_CASE_DIR
import struct


ROOT = Path(__file__).resolve().parents[1]
CASE = SAMPLE_CASE_DIR
ASSETS = ROOT / "mobile/sample-history"


def test_mobile_history_matches_canonical_scans_and_timeline():
    history = json.loads((ASSETS / "history.json").read_text())
    manifest = json.loads((CASE / "manifest.json").read_text())
    timeline = json.loads((CASE / "longitudinal-record.json").read_text())
    assert history["pseudonym"] == manifest["pseudonym"]
    comparison = json.loads((CASE / "derived/progress-01-comparison.json").read_text())
    assert history["specimenId"] == manifest["specimen_id"]
    assert history["summary"].startswith(manifest["pseudonym"])
    scans = {s["filename"]: s for s in manifest["scans"]}
    events = {e["event_id"]: e for e in timeline["events"]}
    for visit in history["visits"]:
        assert visit["date"] == events[visit["id"]]["date"]
        assert [a["filename"] for a in visit["arches"]] == events[visit["id"]]["files"]
        for arch in visit["arches"]:
            scan = scans[arch["filename"]]
            assert arch["displayRotation"] == comparison["display"]["rotation_diagonals"][arch["filename"]]
            assert arch["sha256"] == scan["sha256"]
            assert arch["faceCount"] == scan["face_count"]
            assert arch["units"] == scan["units"]
            png = (ASSETS / arch["previewImage"]).read_bytes()
            assert png[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", png[16:24]) == (840, 728)
