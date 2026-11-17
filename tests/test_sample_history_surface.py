"""Only the explicitly selected local trim can appear as observed geometry."""

import base64
import hashlib
import json

import pytest

from orthoplan import sample_history_surface as history


def test_absent_private_trim_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "SAMPLE_CASE_DIR", tmp_path)
    assert history.local_history_surface() == {"available": False}


def test_local_trim_rejects_replacement_bytes_and_drops_private_annotations(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "SAMPLE_CASE_DIR", tmp_path)
    raw = b"selected surface fixture"
    digest = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(history, "LOWER_CLEAN_SHA256", digest)
    path = tmp_path / "private/surface-edits/week-18-lower-cleaned/repair-bundle.json"
    path.parent.mkdir(parents=True)
    record = {"scan": {"arch": "lower", "sha256": digest, "filename": "trimmed.stl",
                       "repair": {"sourceSha256": history.LOWER_SOURCE_SHA256, "patches": [],
                                  "sourceCapture": "fusion-h-4", "sourceVisit": "progress-02"}},
              "stlBase64": base64.b64encode(raw).decode(), "labels": "private", "notes": "private"}
    path.write_text(json.dumps(record))
    result = history.local_history_surface()
    assert result["available"] and result["sha256"] == digest
    assert "notes" not in result and "labels" not in result
    record["stlBase64"] = base64.b64encode(b"replacement").decode()
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="source/version"):
        history.local_history_surface()
    record["stlBase64"] = base64.b64encode(raw).decode()
    record["scan"]["repair"]["patches"] = [{"estimated": True}]
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="source/version"):
        history.local_history_surface()
