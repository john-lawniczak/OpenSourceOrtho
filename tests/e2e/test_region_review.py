import json
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa:E402
from test_chat_workspace import server_url  # noqa:E402,F401


def test_region_merge_undo_brush_and_export(server_url, tmp_path):  # noqa:F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#loadSample").click()
            expect(page.locator("#reviewStatus")).to_contain_text(
                "0 correction operations", timeout=30000
            )
            page.screenshot(path=str(tmp_path / "sample-boundary-editor.png"), full_page=True)
            page.get_by_text("Advanced: split or merge labels", exact=True).click()
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
