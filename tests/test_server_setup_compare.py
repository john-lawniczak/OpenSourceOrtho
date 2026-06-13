from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from orthoplan.server import Handler


@pytest.fixture()
def server() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _post(port: int, body: bytes, path: str) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    status = resp.status
    payload = json.loads(resp.read() or b"{}")
    conn.close()
    return status, payload


def test_setup_compare_endpoint_returns_live_restage_report(server: int) -> None:
    before = {"id": "before", "stages": [
        {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]}
    ]}
    edited = {"id": "edited", "stages": [
        {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.6}]}
    ]}
    status, payload = _post(
        server,
        json.dumps({"before": before, "edited": edited, "live_restage": True}).encode(),
        "/api/setup-compare",
    )

    assert status == 200
    assert payload["ok"] is True
    assert payload["source"] == "authored"
    assert payload["comparison"]["changed_teeth"][0]["tooth"] == "11"
    assert payload["comparison"]["changed_teeth"][0]["delta"]["translate_x_mm"] == 0.4
