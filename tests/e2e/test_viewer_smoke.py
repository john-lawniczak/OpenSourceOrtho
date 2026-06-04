"""Headless-browser smoke test for the 3D progress viewer.

Skips entirely when Playwright is not installed (so the default `pytest` run
stays green without it). Run the full thing with:

    pip install -e ".[e2e]" && python -m playwright install chromium
    pytest tests/e2e -q

It serves the real dev server, loads the page in headless Chromium, and asserts
the engine responded and the Three.js viewer mounted a sized WebGL canvas with
no uncaught page errors.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import sync_playwright  # noqa: E402

from orthoplan.server import Handler  # noqa: E402


@pytest.fixture(scope="module")
def server_url() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_viewer_renders_3d_canvas(server_url: str) -> None:
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - browser binary may be missing
            pytest.skip(f"playwright chromium unavailable: {exc}")

        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(server_url, wait_until="networkidle")
            # Go to the Review step so the viewer container is visible and sized.
            page.click('button.step[data-step="review"]')
            page.wait_for_selector("#viewer3d canvas", state="attached", timeout=15000)

            box = page.locator("#viewer3d canvas").bounding_box()
            assert box is not None and box["width"] > 0 and box["height"] > 0

            # The engine responded (no offline fallback message).
            findings = page.locator("#findingList").inner_text().lower()
            assert "engine offline" not in findings
        finally:
            browser.close()

    assert not errors, f"uncaught page errors: {errors}"


def test_review_ui_renders_engine_state_and_canvas_pixels(server_url: str) -> None:
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - browser binary may be missing
            pytest.skip(f"playwright chromium unavailable: {exc}")

        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.click('button.step[data-step="review"]')
            page.wait_for_selector("#findingList li", timeout=15000)

            acquisition = page.locator("#acquisitionList").inner_text()
            assert "Root data" in acquisition or "CBCT" in acquisition

            page.click('button.dim[data-dim="2d"]')
            non_background = page.locator("#archCanvas").evaluate(
                """canvas => {
                  const ctx = canvas.getContext('2d');
                  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
                  let changed = 0;
                  for (let i = 0; i < data.length; i += 4) {
                    if (!(data[i] === 251 && data[i + 1] === 253 && data[i + 2] === 254)) changed++;
                  }
                  return changed;
                }"""
            )
            assert non_background > 1000

            page.click('button.step[data-step="stages"]')
            page.fill('input[data-row="0"][data-field="tooth"]', "99")
            page.click('button.step[data-step="review"]')
            page.wait_for_function(
                "() => document.querySelector('#findingList')?.innerText.includes('Plan rejected')"
            )
        finally:
            browser.close()

    assert not errors, f"uncaught page errors: {errors}"
