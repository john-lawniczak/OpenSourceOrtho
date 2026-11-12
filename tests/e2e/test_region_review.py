import json
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa:E402
from test_chat_workspace import server_url  # noqa:E402,F401



@pytest.fixture(autouse=True)
def isolated_corrections(monkeypatch, tmp_path):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "local-labels"))

def test_region_merge_undo_brush_and_export(server_url, tmp_path):  # noqa:F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewLoadupper").click()
            expect(page.locator("#reviewStatus")).to_contain_text(
                "0 correction operations", timeout=30000
            )
            page.screenshot(path=str(tmp_path / "sample-boundary-editor.png"), full_page=True)
            page.get_by_text("Split / merge labels", exact=True).click()
            page.locator("#reviewFrom").fill("21")
            page.locator("#reviewTo").fill("22")
            page.locator("#reviewMerge").click()
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            page.locator("#reviewUndo").click()
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.locator("#reviewTool").select_option("brush")
            page.locator("#reviewTo").fill("13")
            canvas = page.locator("#regionCanvas canvas")
            box = canvas.bounding_box()
            canvas.click(position={"x": box["width"] * 0.5, "y": box["height"] * 0.5})
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            with page.expect_download() as event:
                page.locator("#reviewExport").click()
            file = tmp_path / "corrections.json"
            event.value.save_as(file)
            record = json.loads(file.read_text())
            assert record["schema"] == "ortho-region-corrections-v1"
            assert record["reviewed"] is False and len(record["source_sha256"]) == 64
        finally:
            browser.close()


def test_lower_selection_is_locatable_without_relabeling(server_url, tmp_path):  # noqa: F811
    from test_boundary_intake import export

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewLoadlower").click()
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations", timeout=30000)
            expect(page.locator("#reviewArchNotice")).to_contain_text("Lower · FDI numbering")
            page.locator("#reviewShowLabel").check()
            before = export(page, tmp_path, "before-selection.json")
            page.locator('[data-tooth="46"]').click()
            expect(page.locator("#reviewSelectedTooth")).to_have_text("FDI 46 / US 30 · Lower right first molar")
            expect(page.locator('[data-tooth="46"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#reviewSelectionMarker")).to_have_text("Label 46")
            expect(page.locator("#reviewFocus")).to_be_enabled()
            page.locator("#reviewFocus").click()
            expect(page.locator("#reviewSelectionMarker")).to_be_visible()
            first = page.locator("#regionCanvas").screenshot(path=str(tmp_path / "selected-46.png"))
            page.locator('[data-tooth="31"]').click()
            expect(page.locator("#reviewSelectedTooth")).to_have_text("FDI 31 / US 24 · Lower left central incisor")
            expect(page.locator('[data-tooth="46"]')).to_have_attribute("aria-pressed", "false")
            page.locator("#reviewFocus").click()
            expect(page.locator("#reviewSelectionMarker")).to_have_text("Label 31")
            second = page.locator("#regionCanvas").screenshot(path=str(tmp_path / "selected-31.png"))
            assert first != second
            # Find, select and show other colors must never rewrite saved labels.
            page.locator("#reviewOtherColors").check()
            page.locator('[data-scan-view="fit"]').click()
            assert export(page, tmp_path, "after-selection.json") == before
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.locator("#reviewOtherColors").uncheck()
            page.screenshot(path=str(tmp_path / "lower-selection-guide.png"), full_page=True)
            assert not errors
        finally:
            browser.close()
