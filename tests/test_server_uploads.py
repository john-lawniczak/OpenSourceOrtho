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

ASCII_PLY = """ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
element face 1
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
0 1 0
3 0 1 2
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


def test_upload_scan_rejects_unsupported_filename(server: int) -> None:
    status, payload = _post(
        server,
        ASCII_STL.encode(),
        {"Content-Type": "application/octet-stream", "X-Filename": "notes.txt"},
        "/api/upload/scan",
    )

    assert status == 400
    assert payload["ok"] is False
    assert "supported" in payload["errors"][0]


def test_upload_scan_accepts_ply_and_serves_canonical_stl(
    server: int, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(tmp_path / "workspace"))

    status, payload = _post(
        server,
        ASCII_PLY.encode(),
        {"Content-Type": "application/octet-stream", "X-Filename": "/patient/name/upper.ply"},
        "/api/upload/scan",
    )

    assert status == 200
    assert payload["asset"]["format"] == "ply-ascii"
    assert payload["asset"]["geometry_kind"] == "mesh"
    assert payload["asset"]["face_count"] == 1
    # The registered copy is canonical binary STL, whatever the upload format.
    with urlopen(f"http://127.0.0.1:{server}{payload['url']}", timeout=5) as resp:
        body = resp.read()
    assert resp.headers["Content-Type"] == "model/stl"
    assert len(body) == 84 + 50


def test_upload_scan_accepts_point_cloud_and_serves_xyz(
    server: int, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(tmp_path / "workspace"))

    status, payload = _post(
        server,
        b"0 0 0\n1 0 0\n0 1 0\n",
        {"Content-Type": "application/octet-stream", "X-Filename": "cloud.asc"},
        "/api/upload/scan",
    )

    assert status == 200
    assert payload["asset"]["geometry_kind"] == "points"
    assert payload["asset"]["face_count"] == 0
    assert payload["asset"]["vertex_count"] == 3
    with urlopen(f"http://127.0.0.1:{server}{payload['url']}", timeout=5) as resp:
        assert resp.read().split(b"\n")[0] == b"0.000000 0.000000 0.000000"


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
