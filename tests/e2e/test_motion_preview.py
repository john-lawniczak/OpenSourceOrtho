"""Endpoint-derived simulation is usable, labeled, and isolated from authored planning."""

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_observed_comparison import canvas_snapshot  # noqa: E402


def test_tooth_estimate_selection_and_week_progress(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.locator("#sampleLaunch").click()
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonTooth")).to_be_enabled()
            page.locator("#comparisonTooth").select_option("11")
            page.locator("#comparisonFocusTooth").click()
            page.locator("#comparisonZoomIn").click()
            page.locator('[data-comparison-week="3"]').click()
            expect(page.locator("#comparisonMatchDetail")).to_contain_text("Draft tooth 11")
            expect(page.locator("#comparisonMatchDetail")).to_contain_text("not millimeter measurements")
            canvas = page.locator("#comparisonCanvas canvas")
            third = canvas_snapshot(canvas)
            page.locator("#comparisonTiming").select_option("delayed")
            assert canvas_snapshot(canvas) != third, "Timing selection must change actual estimated poses"
            page.locator("#comparisonTiming").select_option("uniform")
            assert canvas_snapshot(canvas) == third
            page.locator("#sampleComparison details summary").click()
            expect(page.locator("#comparisonProximity")).to_contain_text("Absence does not establish clearance")
            page.locator('[data-comparison-week="5"]').click()
            assert canvas_snapshot(canvas) != third
            page.locator('[data-comparison-week="3"]').click()
            assert canvas_snapshot(canvas) == third, "Selected tooth and camera persist across simulated weeks"
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "selected-tooth-week3.png"))
            page.locator('[data-comparison-arch="lower"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonTooth")).to_have_value("")
            expect(page.locator("#comparisonVisit")).to_contain_text("Week 3 · SIMULATED")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "estimated-mobile.png"))
            assert not errors
        finally:
            browser.close()


def test_failed_motion_preserves_original_scans_and_retries(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.route("**/progress-01-motion-upper.json", lambda route: route.fulfill(status=503, body="unavailable"))
            page.goto(server_url, wait_until="networkidle")
            page.locator("#sampleLaunch").click()
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonVisit")).to_contain_text("observed scan")
            expect(page.locator("#comparisonTooth")).to_be_disabled()
            page.locator('[data-comparison-week="2"]').click()
            expect(page.locator("#comparisonMissing")).to_be_visible()
            expect(page.locator("#comparisonCanvas canvas")).not_to_be_visible()
            page.locator('[data-comparison-week="7"]').click()
            expect(page.locator("#comparisonCanvas canvas")).to_be_visible()
            page.unroute("**/progress-01-motion-upper.json")
            page.locator("#comparisonMotionRetry").click()
            expect(page.locator("#comparisonTooth")).to_be_enabled(timeout=30000)
            page.locator('[data-comparison-week="2"]').click()
            expect(page.locator("#comparisonMissing")).not_to_be_visible()
            expect(page.locator("#comparisonVisit")).to_contain_text("SIMULATED ESTIMATE")
        finally:
            browser.close()
