"""Week 21 history, source downloads and isolated painting saves."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright
from test_chat_workspace import server_url  # noqa: F401


def test_week_twenty_one_history_records_and_painting(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "notes"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("2026-11-23", timeout=60000)
            expect(page.locator("#comparisonVisit")).to_contain_text("exported bite coordinates")
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "observed")
            expect(page.locator("#comparisonNext")).to_be_disabled()
            expect(page.locator("#comparisonTooth")).to_be_disabled()
            page.locator("#comparisonCanvas").screenshot(path=str(tmp_path / "week-21-both.png"))
            page.locator("#comparisonWeek21Records summary").click()
            expect(page.locator("#comparisonWeek21Records img")).to_have_count(6)
            for arch in ["upper", "lower"]:
                link = page.get_by_role("link", name=f"Download week 21 {arch} STL")
                response = page.request.get(server_url + link.get_attribute("href"))
                assert response.ok and len(response.body()) > 10_000_000
            metadata = page.get_by_role("link", name="Redacted PDF and export information")
            data = page.request.get(server_url + metadata.get_attribute("href")).json()
            assert data["export"]["scanner_model"] == "Element 5D"
            assert "332990378" not in str(data) and "Lawniczak" not in str(data)
            page.locator('[data-comparison-week="18"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("approximate bite display", timeout=60000)
            page.locator('[data-comparison-week="20"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "unavailable")
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("2026-11-23", timeout=60000)
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("2026-11-23", timeout=60000)
            page.locator("#comparisonCanvas").screenshot(path=str(tmp_path / "week-21-upper.png"))
            page.get_by_role("link", name="Paint USER_ONE week 21 upper", exact=True).click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSource")).to_contain_text("week 21", timeout=60000)
            editor.locator("#reviewNotes").fill("Week 21 isolated research draft")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSavePath")).to_contain_text("week-21-upper")
            editor.locator("#reviewVisit").select_option("progress-01")
            expect(editor.locator("#reviewSource")).to_contain_text("week 7", timeout=60000)
            expect(editor.locator("#reviewNotes")).to_have_value("")
            editor.locator("#reviewVisit").select_option("progress-03")
            expect(editor.locator("#reviewNotes")).to_have_value("Week 21 isolated research draft", timeout=60000)
            page.locator("#precisionBack").click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#comparisonReset").click()
            page.locator("#comparisonCanvas").scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -150)")
            page.screenshot(path=str(tmp_path / "week-21-mobile-viewport.png"))
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "week-21-mobile.png"))
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
        finally:
            browser.close()


def test_week_twenty_one_failure_and_visit_switch(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.route("**/progress-03-upper.stl", lambda route: route.fulfill(status=503, body="Unavailable"))
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#comparisonStatus")).to_contain_text("HTTP 503", timeout=60000)
            expect(page.locator("#comparisonCanvas")).not_to_be_visible()
            page.locator('[data-comparison-week="4"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "estimated")
            page.unroute("**/progress-03-upper.stl")
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("2026-11-23", timeout=60000)
        finally:
            browser.close()
