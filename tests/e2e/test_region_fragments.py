"""Locate disconnected labels without changing saved tooth memberships."""
import base64
import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import export, surface  # noqa: E402


def test_fragment_inspection_preserves_labels_and_invalidates_after_edits(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html")
            scan = surface(tmp_path).rename(tmp_path / "upper_test.stl")
            page.locator("#reviewScan").set_input_files(scan)
            expect(page.locator("#reviewSource")).to_contain_text("upper_test.stl")
            record = export(page, tmp_path, "empty.json")
            labels = bytearray(record["face_count"])
            labels[0] = labels[1] = labels[-1] = 11
            record["labels_base64"] = base64.b64encode(labels).decode()
            fixture = tmp_path / "patch.json"
            fixture.write_text(json.dumps(record))
            page.locator("#reviewLabels").set_input_files(fixture)
            page.get_by_text("Inspect disconnected patches", exact=True).click()
            page.get_by_role("button", name="Find patches", exact=True).click()
            expect(page.locator("#reviewFragmentSummary")).to_contain_text("Right: 1 · Left: 0")
            expect(page.locator("#reviewFragmentStatus")).to_contain_text("FDI 11 · 1 triangle")
            expect(page.locator("#reviewShowFragments")).to_be_checked()
            page.get_by_role("button", name="Next patch").click()
            page.get_by_label("Highlight patches", exact=True).uncheck()
            assert export(page, tmp_path, "inspected.json") == record
            # Replacing the annotation must remove the now-stale overlay and counts.
            page.locator("#reviewLabels").set_input_files(tmp_path / "empty.json")
            expect(page.locator("#reviewFragmentSummary")).to_contain_text("Labels changed")
            expect(page.locator("#reviewFragmentNext")).to_be_disabled()
            page.get_by_role("button", name="Find patches", exact=True).click()
            expect(page.locator("#reviewFragmentSummary")).to_contain_text("No disconnected")
        finally:
            browser.close()


def test_upper_saved_patch_counts_focus_and_read_only_export(server_url, tmp_path):  # noqa: F811
    case = Path(__file__).resolve().parents[2] / "datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3"
    record = json.loads((case / "annotations/initial-upper-painted-2026-11-12T184456Z.json").read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Pin the historical audit even when a newer checkpoint becomes active.
        page.route("**/api/region-corrections/upper", lambda route: route.fulfill(json={
            "ok": True, "saved": True, "corrections": record, "review_status": "draft",
            "saved_at": "2026-11-12T18:44:56.804533+00:00",
        }))
        try:
            page.goto(server_url + "/region-review.html?baseline=upper")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            page.get_by_text("Inspect disconnected patches", exact=True).click()
            page.get_by_role("button", name="Find patches", exact=True).click()
            expect(page.locator("#reviewFragmentSummary")).to_contain_text("Right: 116 · Left: 144", timeout=30000)
            page.locator("#reviewFragmentChoice").select_option(label="1. FDI 11 · 5 triangles")
            expect(page.locator("#reviewFragmentStatus")).to_contain_text("FDI 11")
            page.locator("#regionCanvas").screenshot(path=str(tmp_path / "upper-patch-closeup.png"))
            page.get_by_role("button", name="Next patch").click()
            expect(page.locator("#reviewFragmentStatus")).to_contain_text("Patch 2 of")
            assert export(page, tmp_path, "upper-inspected.json") == record
            assert not errors
        finally:
            browser.close()
