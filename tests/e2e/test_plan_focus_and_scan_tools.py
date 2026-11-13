"""Focus teeth are display preferences; scan tools preserve the current workflow."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_focus_teeth_toggle_persistence_and_profile_isolation(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(page.locator("#focusTeethInput")).to_have_value("12, 22, 31", timeout=60000)
            expect(page.locator("#sampleReloadPainting")).to_be_enabled(timeout=90000)
            expect(page.locator("#scanRenderStatus")).to_contain_text("Showing your scan", timeout=60000)
            before = page.locator("#planJson").input_value()
            page.locator("#focusTeethToggle").click()
            expect(page.locator("#focusTeethToggle")).to_have_attribute("aria-checked", "true")
            for tooth in [12, 22, 31]:
                expect(page.locator(f'.viewer-tooth-row [data-select-tooth="{tooth}"]')).to_have_class("is-plan-focus")
            assert page.locator("#planJson").input_value() == before
            page.locator("#viewer3d").screenshot(path=str(tmp_path / "focus-teeth.png"))
            page.locator("#focusTeethInput").fill("99")
            page.get_by_role("button", name="Save focus teeth").click()
            expect(page.locator("#focusTeethStatus")).to_contain_text("Check: 99")
            page.locator("#focusTeethInput").fill("12, 31")
            page.get_by_role("button", name="Save focus teeth").click()
            expect(page.locator(".is-plan-focus")).to_have_count(2)
            page.locator("#focusTeethToggle").click()
            expect(page.locator(".is-plan-focus")).to_have_count(0)
            page.locator("#teethProfile").click()
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(page.locator("#focusTeethInput")).to_have_value("")
            page.reload(wait_until="networkidle")
            page.locator("#sampleLaunch").click()
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(page.locator("#focusTeethInput")).to_have_value("12, 31")
            expect(page.locator("#focusTeethToggle")).to_have_attribute("aria-checked", "false")
        finally:
            browser.close()


def test_scan_highlight_toggle_and_compare_return_preserve_history(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            week7 = page.locator('[data-comparison-week="7"]')
            week7.click()
            expect(week7).to_have_css("background-color", "rgb(229, 239, 255)")
            page.locator("#highlightScanWeeks").uncheck()
            expect(week7).not_to_have_css("background-color", "rgb(229, 239, 255)")
            expect(week7).to_contain_text("Observed")
            page.locator("#highlightScanWeeks").check()
            page.locator(".comparison-timeline").screenshot(path=str(tmp_path / "recorded-weeks.png"))
            page.locator("#openScanPair").click()
            tool = page.frame_locator('iframe[title="Compare two scans"]')
            tool.locator("#caseName").fill("Keep this unfinished comparison")
            tool.locator("#progressBack").click()
            expect(page.locator('dialog[aria-label="Compare two scans"]')).to_be_hidden()
            expect(page.locator("#comparisonWeekLabel")).to_have_text("Week 7 of 18")
            expect(page.locator("#openScanPair")).to_be_focused()
            page.locator("#openScanPair").click()
            expect(tool.locator("#caseName")).to_have_value("Keep this unfinished comparison")
            page.locator("#scanPairBack").click()
            expect(page.locator("#sampleComparison")).to_be_visible()
        finally:
            browser.close()
