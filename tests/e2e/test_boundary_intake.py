"""Uploaded geometry reaches a usable, source-bound painting workspace."""
import base64
import hashlib
import json
import re

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_uploaded_intake import intake_server  # noqa: E402,F401


def surface(tmp_path):
    path = tmp_path / "2026-11-12_USER_ONE_lower_test.stl"
    # A gridded XZ surface: source Y, not Z, is its thin dimension.
    records = ["solid synthetic"]
    for x in range(-12, 12, 2):
        for z in range(240, 264, 2):
            a, b, c, d = (x, 0, z), (x+2, 0, z), (x+2, 0, z+2), (x, 0, z+2)
            for triangle in [(a, c, b), (a, d, c)]:
                records += ["facet normal 0 1 0", "outer loop"]
                records += ["vertex " + " ".join(map(str, point)) for point in triangle]
                records += ["endloop", "endfacet"]
    path.write_text("\n".join(records + ["endsolid synthetic"]))
    return path


def export(page, tmp_path, name):
    with page.expect_download() as pending:
        page.locator("#reviewExport").click()
    path = tmp_path / name
    pending.value.save_as(path)
    return json.loads(path.read_text())


def verify_restore_and_rejection(page, tmp_path, painted):
    page.locator("#reviewLabels").set_input_files(tmp_path / "painted.json")
    assert export(page, tmp_path, "restored.json") == painted
    wrong = tmp_path / "wrong-scan.json"
    wrong.write_text(json.dumps({**painted, "source_sha256": "other-scan"}))
    page.locator("#reviewLabels").set_input_files(wrong)
    expect(page.locator("#reviewStatus")).to_contain_text("belongs to another scan")
    assert export(page, tmp_path, "after-rejection.json") == painted


def verify_selected_surface(page, tmp_path, canvas, box, painted):
    page.locator("#reviewShowLabel").check()
    expect(page.locator("#reviewSelectionMarker")).to_have_text("Label 31")
    expect(page.locator("#reviewSelectionMarker")).to_be_visible()
    expect(page.locator("#reviewFocus")).to_be_enabled()
    page.locator('[data-tooth="32"]').click()
    expect(page.locator("#reviewSelectionHelp")).to_contain_text("No surface is labeled 32 yet")
    expect(page.locator("#reviewSelectionMarker")).to_be_hidden()
    expect(page.locator("#reviewFocus")).to_be_disabled()
    page.get_by_role("button", name="Move view", exact=True).click()
    canvas.click(position={"x": box["width"] / 2, "y": box["height"] / 2})
    expect(page.locator("#reviewTo")).to_have_value("31")
    expect(page.locator("#reviewSelectionMarker")).to_have_text("Label 31")
    assert export(page, tmp_path, "after-selection.json") == painted


def continue_in_standalone_editor(page, source):
    editor_url = page.locator('.precision-dialog iframe').get_attribute('src')
    expect(page.frame_locator('.precision-dialog iframe').locator('#reviewSource')).to_contain_text(source.name)
    page.locator('#precisionBack').click()
    # Continue the source-bound paint/undo regression in the standalone editor.
    page.goto(editor_url)
    expect(page).to_have_url(re.compile(r"region-review.html\?edit="))


def verify_unpainted_lower_editor(page):
    expect(page.locator("#reviewArch")).to_have_value("lower")
    expect(page.locator("#reviewTo")).to_have_value("32")
    expect(page.locator("#returnCorrections")).to_be_hidden()
    expect(page.locator("#reviewSelectionHelp")).to_contain_text("No surface is labeled 32 yet")
    expect(page.locator("#reviewSelectionMarker")).to_be_hidden()
    expect(page.locator("#reviewFocus")).to_be_disabled()


def test_upload_handoff_views_and_stroke_undo(intake_server, tmp_path):  # noqa: F811
    source = surface(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(intake_server)
            page.locator("#teethProfile").click()
            page.locator("#simpleStlFile").set_input_files(source)
            expect(page.locator("#boundaryArch")).to_have_value("lower")
            expect(page.locator(".scan-view-controls")).to_be_visible()
            page.screenshot(path=str(tmp_path / "upload-view.png"), full_page=True)
            page.locator('[data-scan-view="roll-right"]').click()
            page.locator("#openBoundaryEditor").click()
            continue_in_standalone_editor(page, source)
            expect(page.locator("#reviewSource")).to_contain_text(source.name)
            verify_unpainted_lower_editor(page)
            original = export(page, tmp_path, "blank.json")
            assert original["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
            assert not any(base64.b64decode(original["labels_base64"]))
            for view in ["roll-left", "roll-right", "flip", "auto"]:
                page.locator(f'[data-scan-view="{view}"]').click()
            after_view = export(page, tmp_path, "view-only.json")
            assert after_view == original
            page.locator('[data-tooth="31"]').click()
            page.get_by_role("button", name="Paint tooth", exact=True).click()
            page.locator("#reviewRadius").fill("3")
            expect(page.locator("#reviewModeHelp")).to_contain_text("Paint tooth 31")
            canvas = page.locator("#regionCanvas canvas")
            canvas.scroll_into_view_if_needed()
            box = canvas.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            page.mouse.move(x-20, y)
            page.mouse.down()
            page.mouse.move(x+20, y, steps=5)
            page.mouse.up()
            expect(page.locator("#reviewStatus")).to_contain_text("1 correction operations")
            painted = export(page, tmp_path, "painted.json")
            assert 31 in base64.b64decode(painted["labels_base64"])
            assert painted["source_sha256"] == original["source_sha256"]
            verify_selected_surface(page, tmp_path, canvas, box, painted)
            page.locator("#reviewUndo").click()
            assert export(page, tmp_path, "undone.json") == original
            page.locator("#reviewRedo").click()
            assert export(page, tmp_path, "redone.json") == painted
            verify_restore_and_rejection(page, tmp_path, painted)
            page.screenshot(path=str(tmp_path / "boundary-workspace.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator('[data-scan-view="fit"]').click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "boundary-mobile.png"), full_page=True)
            assert not errors
        finally:
            browser.close()


def test_own_scan_infers_lower_and_uses_lower_paint_labels(intake_server, tmp_path):  # noqa: F811
    source = surface(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(intake_server + "/region-review.html")
            page.locator("#reviewScan").set_input_files(source)
            expect(page.locator("#reviewSource")).to_contain_text(source.name)
            expect(page.locator("#reviewArch")).to_have_value("lower")
            expect(page.locator('[data-tooth="31"]')).to_be_visible()
            expect(page.locator('[data-tooth="11"]')).to_have_count(0)
            record = export(page, tmp_path, "own-scan.json")
            assert record["arch"] == "lower"
            assert record["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
            assert not any(base64.b64decode(record["labels_base64"]))
        finally:
            browser.close()
