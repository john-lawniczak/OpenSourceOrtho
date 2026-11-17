"""Private edited H6 draft keeps geometry, labels and provenance through the editor."""
import json
from pathlib import Path

import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401

BUNDLE = Path(__file__).resolve().parents[2] / ".orthoplan-region-corrections/USER_ONE/edited-h6-draft/H6-cleaned-painted-draft-repair.json"


def test_edited_h6_draft_import_save_reopen_export(server_url, tmp_path):  # noqa: F811
    if not BUNDLE.exists():
        pytest.skip("Private contributor painting is not distributed")
    original = json.loads(BUNDLE.read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#repairImport").set_input_files(BUNDLE)
            expect(page.locator("#reviewSource")).to_contain_text("442,757 faces", timeout=60000)
            expect(page.locator("#reviewNotes")).to_have_value(original["notes"])
            expect(page.locator("#reviewChecked")).not_to_be_checked()
            page.locator("#regionCanvas").screenshot(path=str(tmp_path / "h6-painted.png"))
            page.locator("#reviewSaveLocal").click()
            expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
            page.goto(server_url)
            page.locator('[data-step-target="notes"]').click()
            page.locator('.painting-note').filter(has_text=original["scan"]["filename"]).get_by_role("link", name="Open painting & notes").click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Restored automatic draft")
            expect(editor.locator("#reviewChecked")).not_to_be_checked()
            corrections = tmp_path / "h6-corrections.json"
            corrections.write_text(json.dumps(original["labels"]))
            editor.locator("#reviewLabels").set_input_files(corrections)
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Unsaved changes")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
            with page.expect_download() as download:
                editor.locator("#reviewExport").click()
            exported = tmp_path / "exported.json"
            download.value.save_as(exported)
            result = json.loads(exported.read_text())
            assert result["stlBase64"] == original["stlBase64"]
            assert result["scan"]["repair"] == original["scan"]["repair"]
            assert result["labels"] == original["labels"]
            assert result["notes"] == original["notes"]
            assert not errors
        finally:
            browser.close()
