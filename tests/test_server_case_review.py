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
    status, payload = resp.status, json.loads(resp.read() or b"{}")
    conn.close()
    return status, payload


def test_case_review_endpoint_returns_mobile_handoff(server: int) -> None:
    plan = {
        "id": "handoff case/upper",
        "title": "Server handoff",
        "stages": [
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]}
        ],
    }
    body = json.dumps({"plan": plan, "base_url": "http://127.0.0.1/app/"}).encode()
    status, payload = _post(server, body, "/api/case-review")

    assert status == 200
    assert payload["ok"] is True
    review = payload["review"]
    assert review["schema"] == "orthoplan-case-review-v1"
    assert review["kind"] == "stored-review"
    assert review["editable"]["requires_browser_engine"] is True
    assert review["handoff"]["open_url"] == "http://127.0.0.1/app/?case=handoff+case%2Fupper"
    assert review["handoff"]["deep_link"] == "orthoplan://case/handoff%20case%2Fupper"
