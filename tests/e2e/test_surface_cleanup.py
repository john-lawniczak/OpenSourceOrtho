"""Surface edits remain reversible copies and gestures keep a stable screen axis."""
import base64
import hashlib
import io
import json
import math

import pytest

pytest.importorskip("playwright.sync_api")
from PIL import Image  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface, export  # noqa: E402
from test_surface_repair import fixture_files  # noqa: E402


def test_trim_protects_teeth_then_previews_undoes_and_reopens(server_url, tmp_path):  # noqa: F811
    stl = surface(tmp_path)
    count = stl.read_text().count("facet normal")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"schema": "ortho-region-corrections-v1",
        "source_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(), "arch": "lower",
        "face_count": count, "labels_base64": base64.b64encode(bytes([31]*count)).decode(),
        "reviewed": False, "provenance": "user-corrected"}))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(stl)
            expect(page.locator("#reviewSource")).to_contain_text(f"{count} faces")
            page.locator("#reviewLabels").set_input_files(labels)
            page.locator("#trimPanel summary").click()
            page.locator('[data-review-mode="trim"]').click()
            canvas = page.locator("#regionCanvas canvas")
            canvas.click()
            expect(page.locator("#trimApply")).to_be_disabled()
            expect(page.locator("#trimStatus")).to_contain_text("0 faces selected")
            page.locator("#trimAllowPainted").check()
            canvas.click()
            expect(page.locator("#trimApply")).to_be_enabled()
            # A selection is only a preview: exporting still returns every face.
            assert export(page, tmp_path, "selected.json")["face_count"] == count
            canvas.screenshot(path=str(tmp_path / "red-trim-selection.png"))
            page.locator("#trimClear").click()
            expect(page.locator("#trimApply")).to_be_disabled()
            canvas.click()
            page.locator("#trimApply").click()
            expect(page.locator("#reviewSource")).to_contain_text("Trimmed surface copy")
            trimmed = export(page, tmp_path, "trimmed.json")
            removed = count - trimmed["labels"]["face_count"]
            assert 0 < removed < count
            assert trimmed["scan"]["repair"]["trims"][0]["removedFaceCount"] == removed
            assert base64.b64decode(trimmed["labels"]["labels_base64"]) == bytes([31]*(count-removed))
            assert "visit" not in trimmed["scan"]
            page.locator("#repairUndo").click()
            expect(page.locator("#reviewSource")).to_contain_text(f"{count} faces")
            assert export(page, tmp_path, "undone.json")["labels_base64"] == json.loads(labels.read_text())["labels_base64"]
            page.on("dialog", lambda dialog: dialog.accept())
            page.locator("#repairImport").set_input_files(tmp_path / "trimmed.json")
            expect(page.locator("#reviewSource")).to_contain_text("Trimmed surface copy")
            page.locator("#reviewNotes").fill("Removed selected mold surface only")
            page.locator("#reviewSaveLocal").click()
            expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
            page.goto(server_url)
            page.locator('[data-step-target="notes"]').click()
            page.locator('.painting-note').filter(has_text=trimmed["scan"]["filename"]).get_by_role("link", name="Open painting & notes").click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSource")).to_contain_text("Trimmed surface copy")
            expect(editor.locator("#reviewNotes")).to_have_value("Removed selected mold surface only")
            assert not errors
        finally:
            browser.close()


def test_brush_rim_selects_without_reframing(server_url, tmp_path):  # noqa: F811
    stl, _ = fixture_files(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(stl)
            expect(page.locator("#reviewSource")).to_contain_text("8 faces")
            page.locator("#repairPanel summary").click()
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("1 patchable opening")
            page.locator("#repairHole").select_option("1")
            expect(page.locator("#repairPreview")).to_be_disabled()
            page.locator("#repairPick").click()
            canvas = page.locator("#regionCanvas canvas")
            box = canvas.bounding_box()
            angle = min(math.radians(36), 2 * math.atan(math.tan(math.radians(18)) * box["width"] / box["height"]))
            distance = math.sqrt(200) / math.sin(angle / 2) * 1.08
            rim_offset = .75 * box["height"] / (2 * distance * math.tan(math.radians(18)))
            canvas.click(position={"x": box["width"] / 2 + rim_offset, "y": box["height"] / 2})
            expect(page.locator("#repairPreview")).to_be_enabled()
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
        finally:
            browser.close()


def test_real_scan_stays_visible_after_finding_holes(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "saves"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-02")
            expect(page.locator("#reviewSource")).to_contain_text("491,548 faces", timeout=60000)
            page.locator("#repairPanel summary").click()
            canvas = page.locator("#regionCanvas canvas")
            before = Image.open(io.BytesIO(canvas.screenshot())).convert("RGB")
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("0 patchable opening", timeout=60000)
            after = Image.open(io.BytesIO(canvas.screenshot(path=str(tmp_path / "scan-after-find.png")))).convert("RGB")
            # Yellow boundary overlay may change a few pixels; the teeth and their
            # screen position must stay intact, including the original framing.
            import numpy as np
            changed = np.any(np.array(before) != np.array(after), axis=2).sum()
            assert changed < before.width * before.height * .01
            page.locator("#trimPanel summary").click()
            page.screenshot(path=str(tmp_path / "cleanup-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "cleanup-mobile.png"), full_page=True)
        finally:
            browser.close()


def test_horizontal_drag_uses_screen_vertical_after_angled_pose(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        try:
            page.goto(server_url + "/region-review.html")
            # Exercise the actual editor and OrbitControls pointer handlers, with
            # an oblique camera like the one left after inspecting a fragment.
            before = page.evaluate("""async () => {
              const {createRegionEditor}=await import('/region_editor_viewer.js');
              const {binaryStl}=await import('/surface_repair_mesh.js');
              const host=document.createElement('div');
              host.id='gesture-test';host.style='position:fixed;inset:0;width:800px;height:600px;z-index:10000';document.body.append(host);
              window.gestureEditor=createRegionEditor(host,{arch:'lower',rotation:[1,1,1],bytes:binaryStl(new Float32Array([0,0,0,1,0,0,0,1,0]))},{onPaint:()=>{},brushSettings:()=>({mode:'orbit',radius:1})});
              gestureEditor.restoreNavigation({position:[40,60,80],target:[0,0,0],up:[0,1,0]});
              return gestureEditor.navigationPose();
            }""")
            canvas = page.locator("#gesture-test canvas")
            canvas.hover(position={"x": 400, "y": 300})
            page.mouse.down()
            page.mouse.move(500, 300, steps=10)
            page.mouse.up()
            after = page.evaluate("gestureEditor.navigationPose()")
            import numpy as np
            direction = np.array(before["position"]) - before["target"]
            direction /= np.linalg.norm(direction)
            up = np.array(before["up"])
            screen_up = up - direction * np.dot(up, direction)
            screen_up /= np.linalg.norm(screen_up)
            new_direction = np.array(after["position"]) - after["target"]
            new_direction /= np.linalg.norm(new_direction)
            assert np.allclose(after["up"], screen_up)
            assert abs(np.dot(new_direction, screen_up)) < 1e-6
            assert not np.allclose(direction, new_direction)
        finally:
            browser.close()
