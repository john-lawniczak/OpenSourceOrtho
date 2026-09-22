"""Own-upload intake regression, independent of the bundled sample fixture."""
from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from orthoplan.server import Handler  # noqa: E402


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


def test_uploaded_scan_readiness_and_resolution_link(intake_server, tmp_path):
    scan = tmp_path / "research-upper.stl"
    scan.write_text("solid test\nfacet normal 0 0 1\nouter loop\n"
                    "vertex 0 0 0\nvertex 60 0 0\nvertex 0 40 0\n"
                    "endloop\nendfacet\nendsolid test\n")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(intake_server)
            page.locator('[data-user-mode="advanced"]').click()
            page.locator('#stlFile').set_input_files(scan)
            page.locator('#scanUnits').select_option('unverified')
            page.locator('[data-step="review"]').click()
            details = page.locator('#intakeReadinessDetails')
            expect(details).to_be_attached()
            details.locator('summary').click()
            assert details.bounding_box()["width"] >= 400
            expect(details).to_contain_text("Scan ")
            expect(details).to_contain_text("Confirm or convert scan coordinates to millimeters")
            expect(details).to_contain_text("Physical validation · Not assessed")
            details.locator('[data-readiness-action="confirm_units"]').click()
            expect(page.locator('#panel-upload')).to_have_class('panel is-active')
            expect(page.locator('#scanUnits')).to_be_focused()
            page.locator('#scanUnits').select_option('mm')
            page.locator('[data-step="review"]').click()
            expect(details).not_to_contain_text("Confirm or convert scan coordinates to millimeters")
            expect(details).to_contain_text("Lower arch · Missing")
            assert not errors
        finally:
            browser.close()
