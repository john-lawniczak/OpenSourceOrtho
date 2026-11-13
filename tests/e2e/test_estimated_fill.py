"""Curved fill previews persist; screen erasing works without a surface hit."""
import json

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_real_curved_upper_fill_preview_adjust_accept_save_and_import(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "saves"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-02")
            expect(page.locator("#reviewSource")).to_contain_text("491,548 faces", timeout=60000)
            page.locator("#repairPanel summary").click()
            page.locator("#repairMaxSize").fill("6")
            page.locator("#repairMaxSize").press("Tab")
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("0 patchable opening", timeout=60000)
            page.locator("#repairHole").select_option("5")
            expect(page.locator("#repairPreview")).to_be_disabled()
            page.locator("#repairEstimate").click()
            expect(page.locator("#repairAccept")).to_be_enabled(timeout=60000)
            page.locator("#regionCanvas").screenshot(path=str(tmp_path / "curved-preview.png"))
            page.locator("#repairFillShape").fill("0.5")
            expect(page.locator("#repairAccept")).to_be_disabled()
            expect(page.locator("#repairFillAmount")).to_have_text("50%")
            page.locator("#repairEstimate").click()
            expect(page.locator("#repairAccept")).to_be_enabled(timeout=60000)
            page.locator("#repairAccept").click()
            expect(page.locator("#reviewSource")).to_contain_text("491,951 faces", timeout=60000)
            page.locator("#reviewNotes").fill("Estimated curved fill; inspect both sides")
            page.locator("#repairSaveCopy").click()
            expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally", timeout=30000)
            with page.expect_download() as download:
                page.locator("#repairExport").click()
            saved = tmp_path / "curved-repair.json"
            download.value.save_as(saved)
            bundle = json.loads(saved.read_text())
            patch = bundle["scan"]["repair"]["patches"][0]
            assert patch["method"] == "adjacent-quadratic-rim-fill"
            assert patch["strength"] == .5
            assert patch["estimated"] is True
            assert patch["firstFace"] == 491548
            page.locator("#repairUndo").click()
            expect(page.locator("#reviewSource")).to_contain_text("491,548 faces")
            other = browser.new_page()
            other.goto(server_url + "/region-review.html")
            other.locator("#repairImport").set_input_files(saved)
            expect(other.locator("#reviewSource")).to_contain_text("491,951 faces", timeout=30000)
            expect(other.locator("#reviewNotes")).to_have_value("Estimated curved fill; inspect both sides")
            assert not errors
        finally:
            browser.close()


def test_screen_eraser_selects_visible_speck_from_empty_space_and_protects_hidden_faces(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        try:
            page.goto(server_url + "/region-review.html")
            await_setup = """async () => {
              const {createRegionEditor}=await import('/region_editor_viewer.js');
              const {binaryStl}=await import('/surface_repair_mesh.js');
              const host=document.createElement('div'); host.id='eraser-test';
              host.style='position:fixed;left:0;top:0;width:800px;height:600px;z-index:10000';document.body.append(host);
              // Display X,Y = source X,Z. Faces 0 and 1 overlap in projection;
              // 0 is nearer the camera. Face 2 is a separate tiny visible speck.
              const raw=new Float32Array([-1,0,-1, 1,0,-1, 0,0,1,
                -1,1,-1, 1,1,-1, 0,1,1,
                2,0,0, 2.1,0,0, 2,0,.1]);
              window.selectedFaces=[];
              window.speckEditor=createRegionEditor(host,{arch:'lower',rotation:[1,1,1],bytes:binaryStl(raw)},
                {brushSettings:()=>({mode:'trim',radius:.5}),onPaint:faces=>{selectedFaces=faces;}});
              speckEditor.colorLabels(new Uint8Array([0,0,0]));
              speckEditor.restoreNavigation({position:[-.55,0,10.5],target:[-.55,0,.5],up:[0,1,0]});
            }"""
            page.evaluate(await_setup)
            canvas = page.locator("#eraser-test canvas")
            # 2 source units project about 185 px from center. The brush center
            # at x=610 misses the tiny triangle, but its circle includes it.
            canvas.hover(position={"x": 610, "y": 300})
            expect(page.locator("#eraser-test .screen-trim-brush")).to_be_visible()
            canvas.click(position={"x": 610, "y": 300})
            assert page.evaluate("selectedFaces") == [2]
            canvas.screenshot(path=str(tmp_path / "speck-eraser.png"))
            canvas.click(position={"x": 400, "y": 300})
            assert page.evaluate("selectedFaces") == [0]
        finally:
            browser.close()
