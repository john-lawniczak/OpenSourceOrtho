from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

import pytest

from orthoplan.server import Handler

ASCII_STL = """solid tooth
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid tooth
"""


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


def _post(port: int, body: bytes, headers: dict[str, str], path: str) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    status = resp.status
    payload = json.loads(resp.read() or b"{}")
    conn.close()
    return status, payload


def test_upload_stl_registers_mesh_and_serves_by_asset_id(server: int, tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(workspace))

    status, payload = _post(
        server,
        ASCII_STL.encode(),
        {"Content-Type": "model/stl", "X-Filename": "/patient/name/upper.stl"},
        "/api/upload/stl",
    )

    assert status == 200
    assert payload["ok"] is True
    assert payload["asset"]["provenance"] == "patient-derived"
    assert payload["asset"]["reference"] == "upper.stl"
    assert payload["asset"]["face_count"] == 1
    with urlopen(f"http://127.0.0.1:{server}{payload['url']}", timeout=5) as resp:
        assert resp.status == 200
        assert resp.read() == ASCII_STL.encode()


def test_upload_stl_rejects_non_stl_filename(server: int) -> None:
    status, payload = _post(
        server,
        ASCII_STL.encode(),
        {"Content-Type": "application/octet-stream", "X-Filename": "upper.obj"},
        "/api/upload/stl",
    )

    assert status == 400
    assert payload["ok"] is False


def test_upload_case_record_registers_local_metadata(server: int, tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(workspace))

    status, payload = _post(
        server,
        b"DICM" + b"\x00" * 12,
        {
            "Content-Type": "application/dicom",
            "X-Filename": "/patients/jane-doe/cbct/series-1.dcm",
            "X-Record-Kind": "cbct",
            "X-Modality": "CBCT/DICOM",
        },
        "/api/upload/record",
    )

    assert status == 200
    assert payload["ok"] is True
    record = payload["record"]
    assert record["kind"] == "cbct"
    assert record["modality"] == "CBCT/DICOM"
    assert record["filename"] == "series-1.dcm"
    assert "jane-doe" not in json.dumps(record)
    assert record["local_reference"].startswith("records/")
    assert (workspace / record["local_reference"]).read_bytes().startswith(b"DICM")


def test_upload_case_record_rejects_unknown_kind(server: int) -> None:
    status, payload = _post(
        server,
        b"data",
        {"Content-Type": "application/octet-stream", "X-Record-Kind": "root-bone-aware"},
        "/api/upload/record",
    )

    assert status == 400
    assert payload["ok"] is False
