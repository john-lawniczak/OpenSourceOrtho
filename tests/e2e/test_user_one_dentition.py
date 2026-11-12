"""USER_ONE loads the published draft and disables reported removed teeth only for this case."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_published_upper_labels_and_case_specific_inventory(server_url, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "empty-local-labels"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper", wait_until="load")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            expect(page.locator('[data-tooth="18"]')).to_be_disabled()
            expect(page.locator('[data-tooth="28"]')).to_be_disabled()
            expect(page.locator('[data-tooth="17"]')).to_be_enabled()
            expect(page.locator('[data-tooth="27"]')).to_be_enabled()
            expect(page.locator("#reviewSaveStatus")).to_contain_text("Published draft")
            page.locator('[data-tooth="27"]').click()
            expect(page.locator("#reviewSelectionHelp")).to_contain_text("21,856 labeled faces")
            expect(page.locator("#reviewSelectedTooth")).to_contain_text("US 15")
            page.get_by_role("button", name="Above", exact=True).click()
            page.screenshot(path=str(tmp_path / "upper-posterior-draft.png"), full_page=True)
        finally:
            browser.close()
