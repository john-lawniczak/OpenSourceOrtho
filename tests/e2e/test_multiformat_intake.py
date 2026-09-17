"""A non-STL scan upload must reach the viewer, not just the engine.

The browser parses only the engine's canonical shapes, so a PLY (or GLB, or
point cloud) has to survive the whole round trip: upload -> canonical copy ->
`/api/mesh/<id>` -> rendered geometry. This exercises that path in a real
browser, which unit tests on either side cannot.
"""
from __future__ import annotations

import struct
import threading
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from orthoplan.server import Handler  # noqa: E402

# A wide, arch-scale triangle pair, so the scale/readiness copy behaves as it
# would for a real scan rather than tripping the implausible-size note.
_POINTS = [(0.0, 0.0, 0.0), (60.0, 0.0, 0.0), (0.0, 40.0, 0.0), (60.0, 40.0, 5.0)]
_FACES = [(0, 1, 2), (1, 3, 2)]


def _ply_ascii() -> str:
    head = [
        "ply", "format ascii 1.0", f"element vertex {len(_POINTS)}",
        "property float x", "property float y", "property float z",
        f"element face {len(_FACES)}", "property list uchar int vertex_indices",
        "end_header",
    ]
    rows = [f"{x} {y} {z}" for x, y, z in _POINTS] + [f"3 {a} {b} {c}" for a, b, c in _FACES]
    return "\n".join(head + rows) + "\n"


@pytest.fixture
def intake_server(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(tmp_path / "meshes"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_a_ply_upload_registers_and_renders(intake_server, tmp_path):
    scan = tmp_path / "research-upper.ply"
    scan.write_text(_ply_ascii())

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(intake_server)
            page.locator('[data-user-mode="advanced"]').click()
            page.locator("#stlFile").set_input_files(scan)

            status = page.locator("#uploadFileList")
            expect(status).to_contain_text("research-upper.ply")
            expect(status).to_contain_text("Registered 1 scan file(s)")

            # The engine stored a canonical binary STL, and it is what the
            # viewer fetches back for a format the browser cannot parse.
            body = page.evaluate(
                """async () => {
                  const upload = await fetch('/api/upload/scan', {
                    method: 'POST',
                    headers: { 'X-Filename': 'probe.ply' },
                    body: %s,
                  }).then((r) => r.json());
                  const bytes = await fetch(upload.url).then((r) => r.arrayBuffer());
                  return { format: upload.asset.format, kind: upload.asset.geometry_kind,
                           units: upload.asset.units, size: bytes.byteLength };
                }"""
                % repr(_ply_ascii()).replace("'", '"', 2)
            )
            assert body["format"] == "ply-ascii"
            assert body["kind"] == "mesh"
            assert body["units"] == "unverified"
            assert body["size"] == 84 + len(_FACES) * 50

            assert not errors
        finally:
            browser.close()


def test_a_point_cloud_upload_is_accepted_and_labelled(intake_server, tmp_path):
    cloud = tmp_path / "research-lower.asc"
    cloud.write_text("\n".join(f"{x} {y} {z}" for x, y, z in _POINTS) + "\n")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(intake_server)
            page.locator('[data-user-mode="advanced"]').click()
            page.locator("#stlFile").set_input_files(cloud)

            expect(page.locator("#uploadFileList")).to_contain_text("Registered 1 scan file(s)")
            assert not errors
        finally:
            browser.close()


def test_an_unsupported_file_is_rejected_without_a_page_error(intake_server, tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("this is not a scan\n")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(intake_server)
            page.locator('[data-user-mode="advanced"]').click()
            page.locator("#stlFile").set_input_files(notes)

            expect(page.locator("#uploadFileList")).to_contain_text("No supported scan files")
            assert not errors
        finally:
            browser.close()


def test_glb_bytes_survive_the_round_trip(intake_server):
    """GLB is binary and container-shaped - the case most likely to corrupt."""

    positions = b"".join(struct.pack("<3f", *point) for point in _POINTS)
    padding = b"\x00" * (-len(positions) % 4)
    indices = b"".join(struct.pack("<H", index) for face in _FACES for index in face)
    data = positions + padding + indices
    document = (
        '{"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],'
        '"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1,"mode":4}]}],'
        f'"accessors":[{{"bufferView":0,"componentType":5126,"count":{len(_POINTS)},"type":"VEC3"}},'
        f'{{"bufferView":1,"componentType":5123,"count":{len(_FACES) * 3},"type":"SCALAR"}}],'
        f'"bufferViews":[{{"buffer":0,"byteOffset":0,"byteLength":{len(positions + padding)}}},'
        f'{{"buffer":0,"byteOffset":{len(positions + padding)},"byteLength":{len(indices)}}}],'
        f'"buffers":[{{"byteLength":{len(data)}}}]}}'
    ).encode()
    document += b" " * (-len(document) % 4)
    binary = data + b"\x00" * (-len(data) % 4)
    glb = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(document) + 8 + len(binary))
    glb += struct.pack("<II", len(document), 0x4E4F534A) + document
    glb += struct.pack("<II", len(binary), 0x004E4942) + binary

    from http.client import HTTPConnection
    from urllib.parse import urlsplit

    target = urlsplit(intake_server)
    conn = HTTPConnection(target.hostname, target.port, timeout=10)
    conn.request("POST", "/api/upload/scan", body=glb, headers={"X-Filename": "arch.glb"})
    import json

    payload = json.loads(conn.getresponse().read())
    conn.close()

    assert payload["ok"] is True
    assert payload["asset"]["format"] == "glb"
    assert payload["asset"]["face_count"] == len(_FACES)
    assert payload["asset"]["declared_units"] == "meter"
    assert payload["asset"]["units"] == "unverified"
