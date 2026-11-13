"""Slow file reads must not replace edits made after import was requested."""
import json

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_surface_repair import fixture_files  # noqa: E402


def bundle_file(page, stl, tmp_path, name="incoming.json", notes="Imported notes"):
    bundle = page.evaluate("""async ([raw,notes]) => {
      const {appendSurfacePatch,meshHash}=await import('/surface_repair_mesh.js');
      const {repairBundle}=await import('/surface_repair_bundle.js');
      const {RegionEdits}=await import('/region_edits.js');
      const {proposePatch}=await import('/surface_patch.js');
      const bytes=new Uint8Array(raw).buffer;
      const scan={bytes,sha256:await meshHash(bytes),filename:'upper.stl',arch:'upper',rotation:[1,1,1]};
      const next=await appendSurfacePatch(scan,new Uint8Array(8),proposePatch([[-.5,-.5,0],[.5,-.5,0],[.5,.5,0],[-.5,.5,0]],3));
      return repairBundle(next.scan,new RegionEdits(next.labels,'upper'),notes);
    }""", [list(stl.read_bytes()), notes])
    path = tmp_path / name
    path.write_text(json.dumps(bundle))
    return path


def delay_file_read(page, name, method):
    page.evaluate("""([name,method]) => {
      const digest=crypto.subtle.digest.bind(crypto.subtle); window.completedHashes=0;
      crypto.subtle.digest=async (...args)=>{ const result=await digest(...args); window.completedHashes++; return result; };
      const original=File.prototype[method];
      File.prototype[method]=async function(...args) {
        if(this.name===name) { window.readStarted=true; await new Promise(resolve=>window.releaseRead=resolve); }
        return original.apply(this,args);
      };
    }""", [name, method])


@pytest.mark.parametrize("kind", ["repair", "scan", "labels"])
def test_import_preserves_notes_typed_while_reading(server_url, tmp_path, kind):  # noqa: F811
    stl, labels = fixture_files(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(stl)
            expect(page.locator("#reviewSource")).to_contain_text("8 faces")
            source = page.locator("#reviewSource").inner_text()
            incoming = bundle_file(page, stl, tmp_path) if kind == "repair" else labels
            if kind == "scan":
                incoming = tmp_path / "replacement-upper.stl"
                incoming.write_bytes(stl.read_bytes())
            field = {"repair": "repairImport", "scan": "reviewScan", "labels": "reviewLabels"}[kind]
            delay_file_read(page, incoming.name, "arrayBuffer" if kind == "scan" else "text")
            page.locator(f"#{field}").set_input_files(incoming)
            page.wait_for_function("window.readStarted")
            page.locator("#reviewNotes").fill("New notes must survive")
            page.evaluate("window.releaseRead()")
            status = "repairStatus" if kind == "repair" else "reviewStatus"
            expect(page.locator(f"#{status}")).to_contain_text("Import stopped")
            expect(page.locator("#reviewSource")).to_have_text(source)
            expect(page.locator("#reviewNotes")).to_have_value("New notes must survive")
            assert not errors
        finally:
            browser.close()


def test_newer_repair_import_wins_over_slow_previous_file(server_url, tmp_path):  # noqa: F811
    stl, _ = fixture_files(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url + "/region-review.html")
            old = bundle_file(page, stl, tmp_path, "old.json", "Old notes")
            new = bundle_file(page, stl, tmp_path, "new.json", "Latest notes")
            delay_file_read(page, old.name, "text")
            page.locator("#repairImport").set_input_files(old)
            page.wait_for_function("window.readStarted")
            page.locator("#repairImport").set_input_files(new)
            expect(page.locator("#reviewNotes")).to_have_value("Latest notes")
            page.evaluate("window.releaseRead()")
            # Wait for both imports' hash checks, including the delayed one.
            page.wait_for_function("window.completedHashes === 2")
            expect(page.locator("#reviewNotes")).to_have_value("Latest notes")
            expect(page.locator("#reviewSource")).to_contain_text("12 faces")
        finally:
            browser.close()
