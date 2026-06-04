from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
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


def _get(port: int, path: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _post(port: int, body: bytes, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/evaluate", body=body, headers=headers or {})
    resp = conn.getresponse()
    status = resp.status
    payload = json.loads(resp.read() or b"{}")
    conn.close()
    return status, payload


def test_serves_index(server: int) -> None:
    status, body = _get(server, "/")
    assert status == 200
    assert b"OpenSource Ortho" in body


def test_path_traversal_is_blocked(server: int) -> None:
    status, _ = _get(server, "/../orthoplan/api.py")
    assert status == 404
    status, _ = _get(server, "/%2e%2e/orthoplan/server.py")
    assert status == 404


def test_valid_evaluate_returns_findings(server: int) -> None:
    plan = {
        "id": "p",
        "stages": [
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.5}]}
        ],
    }
    status, payload = _post(server, json.dumps(plan).encode(), {"Content-Type": "application/json"})
    assert status == 200
    assert payload["ok"] is True
    assert any("linear cap" in f["title"] for f in payload["findings"])


def test_invalid_json_is_400(server: int) -> None:
    status, payload = _post(server, b"not json", {"Content-Type": "application/json"})
    assert status == 400
    assert payload["ok"] is False


def test_empty_body_is_400(server: int) -> None:
    status, payload = _post(server, b"")
    assert status == 400
    assert payload["ok"] is False


def test_malformed_content_length_does_not_crash(server: int) -> None:
    # A bad Content-Length must yield a clean 400, not a dropped connection.
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.putrequest("POST", "/api/evaluate")
    conn.putheader("Content-Length", "not-a-number")
    conn.endheaders()
    conn.send(b"{}")
    resp = conn.getresponse()
    assert resp.status == 400
    conn.close()


def test_oversized_body_is_413(server: int) -> None:
    # Declare a length over the cap without sending the bytes; the server must
    # reject on the declared length before reading.
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.putrequest("POST", "/api/evaluate")
    conn.putheader("Content-Length", str(6 * 1024 * 1024))
    conn.endheaders()
    resp = conn.getresponse()
    assert resp.status == 413
    conn.close()


def test_unknown_post_endpoint_is_404(server: int) -> None:
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.request("POST", "/api/other", body=b"{}", headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()
