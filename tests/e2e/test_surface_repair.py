"""Small-hole patches preserve labels and persist as visibly estimated copies."""
import base64
import hashlib
import json
import struct

import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def fixture_files(tmp_path):
    outer = [(-10, -10, 0), (10, -10, 0), (10, 10, 0), (-10, 10, 0)]
    inner = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces += [(outer[i], outer[j], inner[j]), (outer[i], inner[j], inner[i])]
    raw = b"Synthetic ring".ljust(80, b"\0") + struct.pack("<I", len(faces))
    for face in faces:
        raw += struct.pack("<12fH", 0, 0, 1, *(v for p in face for v in p), 0)
    stl = tmp_path / "repair-upper.stl"
    stl.write_bytes(raw)
    labels = {"schema": "ortho-region-corrections-v1", "source_sha256": hashlib.sha256(raw).hexdigest(),
              "arch": "upper", "face_count": 8, "labels_base64": base64.b64encode(bytes([12]*8)).decode(),
              "reviewed": False, "provenance": "user-corrected"}
    label_path = tmp_path / "labels.json"
    label_path.write_text(json.dumps(labels))
    return stl, label_path


def test_repair_preview_undo_save_reopen_and_bundle(server_url, tmp_path):  # noqa: F811
    stl, labels = fixture_files(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(stl)
            expect(page.locator("#reviewSource")).to_contain_text("8 faces")
            page.locator("#reviewLabels").set_input_files(labels)
            page.locator("#repairPanel summary").click()
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("1 patchable opening")
            expect(page.locator("#repairAccept")).to_be_disabled()
            page.locator("#repairPreview").click()
            expect(page.locator("#repairAccept")).to_be_enabled()
            page.locator("#repairCancel").click()
            expect(page.locator("#repairAccept")).to_be_disabled()
            page.locator("#repairPreview").click()
            page.locator("#regionCanvas").screenshot(path=str(tmp_path / "preview.png"))
            page.locator("#repairAccept").click()
            expect(page.locator("#reviewSource")).to_contain_text("12 faces")
            expect(page.locator("#reviewSource")).to_contain_text("Estimated repaired surface")
            page.locator("#repairEstimated").uncheck()
            page.locator("#repairEstimated").check()
            page.locator("#repairUndo").click()
            expect(page.locator("#reviewSource")).to_contain_text("8 faces")
            expect(page.locator("#repairEstimated")).to_be_disabled()
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("1 patchable opening")
            page.locator("#repairPreview").click()
            page.locator("#repairAccept").click()
            expect(page.locator("#reviewSource")).to_contain_text("12 faces")
            page.locator("#reviewNotes").fill("Estimated model gap; inspect new faces")
            page.locator("#reviewSaveLocal").click()
            expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally")
            with page.expect_download() as download:
                page.locator("#repairExport").click()
            bundle_path = tmp_path / "repair.json"
            download.value.save_as(bundle_path)
            bundle = json.loads(bundle_path.read_text())
            assert base64.b64decode(bundle["labels"]["labels_base64"]) == bytes([12]*8 + [0]*4)
            assert bundle["scan"]["repair"]["originalFaceCount"] == 8
            assert "visit" not in bundle["scan"]
            page.locator("#regionCanvas").screenshot(path=str(tmp_path / "accepted.png"))
            page.goto(server_url)
            page.locator('[data-step-target="notes"]').click()
            page.locator('.painting-note').filter(has_text="repair-upper-repaired-1.stl").get_by_role("link", name="Open painting & notes").click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSource")).to_contain_text("Estimated repaired surface")
            expect(editor.locator("#reviewNotes")).to_have_value("Estimated model gap; inspect new faces")
            expect(editor.locator("#repairEstimated")).to_be_checked()
            verify_bundle_import(browser, server_url, bundle_path)
            assert not errors
        finally:
            browser.close()


def verify_bundle_import(browser, base_url, bundle_path):
    """Portable bundles retain estimated face ranges in a fresh browser context."""
    other = browser.new_page()
    other.goto(base_url + "/region-review.html")
    other.locator("#repairImport").set_input_files(bundle_path)
    expect(other.locator("#reviewSource")).to_contain_text("12 faces")
    expect(other.locator("#reviewNotes")).to_have_value("Estimated model gap; inspect new faces")
    other.locator("#repairPanel summary").click()
    expect(other.locator("#repairEstimated")).to_be_checked()
    other.close()


def test_real_week_eighteen_keeps_complex_boundaries_unpatched(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-02&capture=upper-clean")
            expect(page.locator("#reviewSource")).to_contain_text("491,548 faces", timeout=60000)
            before = page.locator("#reviewSource").inner_text()
            page.locator("#repairPanel summary").click()
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("0 patchable opening(s)", timeout=60000)
            expect(page.locator("#repairAccept")).to_be_disabled()
            page.locator("#repairMaxSize").fill("6")
            page.locator("#repairMaxSize").press("Tab")
            page.locator("#repairFind").click()
            expect(page.locator("#repairStatus")).to_contain_text("0 patchable opening(s)", timeout=60000)
            expect(page.locator("#reviewSource")).to_have_text(before)
            page.locator("#repairHole").select_option("5")
            expect(page.locator("#repairStatus")).to_contain_text("curved")
            expect(page.locator("#repairPreview")).to_be_disabled()
            page.screenshot(path=str(tmp_path / "real-repair-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "real-repair-mobile.png"), full_page=True)
        finally:
            browser.close()
