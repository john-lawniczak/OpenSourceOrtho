"""End-to-end checks for the POST /api/segment route and mesh serving."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from orthoplan.server import Handler


@pytest.fixture()
def server() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(port: int, path: str) -> tuple[int, bytes]:
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, body


def _post(port: int, payload: dict) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=30)
    conn.request(
        "POST",
        "/api/segment",
        body=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    data = json.loads(resp.read() or b"{}")
    conn.close()
    return resp.status, data


def test_segment_endpoint_rejects_unresolvable_scan(server: int) -> None:
    status, payload = _post(server, {"scans": [{"reference": "nope.stl", "arch": "maxillary"}]})
    assert status == 200
    assert payload["ok"] is False
    assert payload["errors"]


def test_segment_endpoint_proposes_and_serves_meshes(
    server: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(tmp_path))
    status, payload = _post(
        server,
        {
            "scans": [
                {
                    "reference": "example-scans/canonical-orthocad-001/sample-test-case-upper.stl",
                    "arch": "maxillary",
                }
            ]
        },
    )
    assert status == 200, payload
    assert payload["ok"] is True
    assert payload["requires_review"] is True
    assert payload["teeth"]
    sample_points = payload["plan_fragment"]["tooth_meshes"][0]["surface_sample_points"]
    assert sample_points
    assert len(sample_points) <= 64
    # A proposed per-tooth mesh is served back over the registered-mesh route.
    mesh_status, body = _get(server, payload["teeth"][0]["url"])
    assert mesh_status == 200
    assert len(body) > 84
