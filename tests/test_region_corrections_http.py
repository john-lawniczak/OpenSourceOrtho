"""Local save endpoints share the server's request and asset boundaries."""
import json

import pytest

from test_server import _get, _post, server  # noqa: F401
from test_region_corrections import record


def test_baseline_save_http_roundtrip_and_private_storage(server, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    body = json.dumps({"arch": "lower", "corrections": record(), "notes": "Local draft"}).encode()
    status, saved = _post(server, body, {"Content-Type": "application/json"}, "/api/region-corrections")
    assert status == 200 and saved["ok"]
    status, body = _get(server, "/api/region-corrections/lower")
    loaded = json.loads(body)
    assert status == 200 and loaded["corrections"] == saved["corrections"]
    assert loaded["notes"] == "Local draft"
    assert _get(server, "/.orthoplan-region-corrections/USER_ONE/baseline-lower")[0] == 404


def test_cross_origin_save_is_rejected_before_writing(server, monkeypatch):  # noqa: F811
    def unexpected(*args):
        pytest.fail("Foreign page reached annotation storage")
    monkeypatch.setattr("orthoplan.server.save_baseline_corrections", unexpected)
    status, _ = _post(server, b'{}', {"Origin": "https://untrusted.example"}, "/api/region-corrections")
    assert status == 403


def test_week_seven_http_roundtrip_is_separate_from_week_one(server, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    body = json.dumps({"arch": "upper", "visit": "progress-01",
                       "corrections": record("upper", visit="progress-01")}).encode()
    status, saved = _post(server, body, {"Content-Type": "application/json"}, "/api/region-corrections")
    assert status == 200 and saved["ok"]
    status, body = _get(server, "/api/region-corrections/upper?visit=progress-01")
    assert status == 200 and json.loads(body)["corrections"] == saved["corrections"]
    assert json.loads(_get(server, "/api/region-corrections/upper")[1]) == {"ok": True, "saved": False}
    assert json.loads(_get(server, "/api/region-corrections/upper?visit=progress-02")[1]) == {"ok": True, "saved": False}
    assert not json.loads(_get(server, "/api/region-corrections/upper?visit=progress-03")[1])["ok"]
