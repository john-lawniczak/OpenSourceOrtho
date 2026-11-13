"""The sample defaults to simultaneous upper/lower progression."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def canvas_snapshot(page):
    canvas = page.locator("#comparisonCanvas canvas")
    # Keep the sticky step rail outside the capture when controls scroll the page.
    canvas.evaluate("el => el.scrollIntoView({block: 'center'})")
    return canvas.screenshot()


def test_both_arches_default_zoom_and_dark_week_selection(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonCanvas canvas")).to_have_count(1)
            expect(page.locator("#comparisonCanvas canvas")).to_have_attribute("aria-label", "Upper and lower teeth together; drag to rotate, scroll to zoom, double-click a crown to focus")
            expect(page.locator('[data-comparison-arch="both"]')).to_have_attribute("aria-pressed", "true")
            page.locator('[data-comparison-week="4"]').click()
            expect(page.locator('[data-comparison-week="4"]')).to_have_attribute("aria-current", "step")
            page.locator("#themeToggle").click()
            selected = page.locator('[data-comparison-week="4"]')
            assert selected.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(64, 52, 30)"
            assert selected.evaluate("e => getComputedStyle(e).boxShadow") != "none"
            page.locator("#highlightEstimatedWeeks").uncheck()
            assert selected.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(15, 118, 110)"
            page.locator("#highlightEstimatedWeeks").check()
            before = canvas_snapshot(page)
            page.locator("#comparisonZoomIn").click()
            assert canvas_snapshot(page) != before
            page.locator("#comparisonReset").click()
            assert canvas_snapshot(page) == before
            expect(page.get_by_text("Scan dates and accuracy", exact=True)).to_have_count(0)
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "both-arches.png"))
            page.locator("#comparisonTooth").select_option("33")
            page.locator("#comparisonFocusTooth").click()
            focused = canvas_snapshot(page)
            page.locator('[data-comparison-week="7"]').click()
            page.locator('[data-comparison-week="4"]').click()
            assert canvas_snapshot(page) == focused
        finally:
            browser.close()
