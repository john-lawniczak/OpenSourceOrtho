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
