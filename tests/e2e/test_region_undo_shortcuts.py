"""Painting undo uses platform shortcuts without stealing text-input undo."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import export, surface  # noqa: E402


def test_command_control_undo_redo_and_text_focus(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(surface(tmp_path))
            expect(page.locator("#reviewSource")).to_contain_text("lower_test.stl")
            expect(page.locator("#reviewShowLabel")).not_to_be_checked()
            empty = export(page, tmp_path, "empty.json")
            page.get_by_role("button", name="Paint tooth", exact=True).click()
            page.locator("#regionCanvas canvas").click()
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            painted = export(page, tmp_path, "painted.json")
            assert painted != empty
            for modifier in ["Meta", "Control"]:
                page.keyboard.press(f"{modifier}+z")
                expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
                assert export(page, tmp_path, f"undo-{modifier}.json") == empty
                page.keyboard.press(f"{modifier}+Shift+z")
                expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
                assert export(page, tmp_path, f"redo-{modifier}.json") == painted
            # Numeric fields and notes keep native undo instead of undoing paint.
            page.locator("#reviewRadius").fill("2")
            page.locator("#reviewRadius").press("Meta+z")
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
            page.locator("#reviewNotes").press_sequentially("keep text undo local")
            page.locator("#reviewNotes").press("Meta+z")
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            assert export(page, tmp_path, "after-text-undo.json") == painted
        finally:
            browser.close()
