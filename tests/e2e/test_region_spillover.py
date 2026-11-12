"""Visible source/destination controls protect unrelated labels while painting."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface  # noqa: E402


def test_spillover_workflow_and_tooth_names(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html", wait_until="load")
            scan = surface(tmp_path)
            scan = scan.rename(tmp_path / "upper_test.stl")
            page.locator("#reviewScan").set_input_files(scan)
            expect(page.locator("#reviewSource")).to_contain_text("upper_test.stl")
            expect(page.locator('[data-tooth="25"]')).to_contain_text("Premolar 2")
            expect(page.locator('[data-tooth="26"]')).to_contain_text("Molar 1")
            expect(page.locator('[data-tooth="27"]')).to_contain_text("Molar 2")
            page.locator('[data-tooth="25"]').click()
            page.get_by_role("button", name="Correct spillover").click()
            expect(page.locator("#reviewSplitSource")).to_have_value("25")
            expect(page.locator("#reviewSplitHint")).to_contain_text("choose the correct destination")
            expect(page.get_by_role("button", name="Flip direction")).to_be_disabled()
            page.locator('[data-tooth="26"]').click()
            expect(page.locator("#reviewSplitHint")).to_contain_text("25 → 26")
            expect(page.locator("#reviewTool")).to_have_value("split")
            page.get_by_role("button", name="Flip direction").click()
            expect(page.locator("#reviewSplitSource")).to_have_value("26")
            expect(page.locator("#reviewFrom")).to_have_value("26")
            expect(page.locator("#reviewTo")).to_have_value("25")
            expect(page.locator('[data-tooth="25"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#reviewSplitHint")).to_contain_text("26 → 25")
            expect(page.locator("#reviewTool")).to_have_value("split")
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.get_by_role("button", name="Flip direction").click()
            expect(page.locator("#reviewSplitHint")).to_contain_text("25 → 26")
            page.locator("#reviewSplitSource").select_option("0")
            expect(page.get_by_role("button", name="Flip direction")).to_be_disabled()
            page.locator("#reviewSplitSource").select_option("27")
            expect(page.locator("#reviewFrom")).to_have_value("27")
            page.get_by_label("Label edges", exact=True).uncheck()
            page.get_by_role("button", name="Move view", exact=True).click()
            expect(page.locator("#reviewSplitPanel")).to_be_hidden()
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.screenshot(path=str(tmp_path / "spillover-controls.png"), full_page=True)
        finally:
            browser.close()
