from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Page, sync_playwright  # noqa: E402

from orthoplan.server import Handler  # noqa: E402


@pytest.fixture(scope="module")
def server_url() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def advance(page: Page, step: str) -> None:
    page.click("#guidedNext")
    panel = f'#guided .gstep[data-gstep="{step}"].is-active'
    page.wait_for_selector(panel)
    page.wait_for_function(
        """selector => {
          const panel = document.querySelector(selector);
          const heading = panel?.querySelector('h3');
          const top = panel?.getBoundingClientRect().top ?? -1;
          return document.activeElement === heading && top >= 55 && top < 180;
        }""",
        arg=panel,
    )


def test_sample_guided_flow_stays_focused_and_progressively_disclosed(server_url: str) -> None:
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"playwright chromium unavailable: {exc}")

        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(server_url, wait_until="networkidle")
            assert page.locator("body").get_attribute("data-chat-collapsed") == "1"
            page.click("#sampleLaunch")
            page.wait_for_selector('body[data-sample="1"]')
            assert not page.locator("#guidedPrintLinks").is_visible()

            advance(page, "plan")
            assert page.locator("#guidedBuild").inner_text() == "Rebuild sample plan"
            assert "Rebuilding is optional" in page.locator("#guidedBuildStatus").inner_text()
            trust_text = page.locator("#trustStatusStrip").inner_text()
            scan_text = page.locator("#scanRenderStatus").inner_text()
            if "Segmenting individual teeth" in scan_text:
                assert "Processing locally" in trust_text

            page.wait_for_function(
                "() => document.querySelector('#trustStatusStrip')?.innerText.includes('Applied draft')"
            )
            assert page.locator("#anatomyReviewList [data-anatomy-review]").count() == 0
            assert "Technician mode" in page.locator("#anatomyReviewList").inner_text()

            advance(page, "details")
            advance(page, "review")
            dashboard = page.locator("#guidedReviewDashboard").inner_text()
            assert "Cannot assess fully" not in dashboard
            assert "Crown contact / spacing" in dashboard

            advance(page, "preview")
            assert not page.locator("#guidedPreviewHost .manual-edit").is_visible()
            hidden_modes = page.locator("#guidedPreviewHost .viewer-toolbar > button.mode")
            assert hidden_modes.count() == 3
            assert all(not item.is_visible() for item in hidden_modes.all())

            advance(page, "print")
            print_step = page.locator('#guided .gstep[data-gstep="print"]')
            assert "models are not trays or aligner shells" in print_step.inner_text()
            assert not page.locator("#guidedPrintLinks").is_visible()
        finally:
            browser.close()

    assert not errors, f"uncaught page errors: {errors}"
