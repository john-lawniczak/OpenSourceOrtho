"""Suggested week 18 surfaces open their installed automatic draft colors."""
import json

import pytest
pytest.importorskip("playwright.sync_api")
pytest.importorskip("numpy")
pytest.importorskip("scipy")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from tools.seed_week_eighteen_labels import OUTPUT, install  # noqa: E402


def test_suggested_pair_loads_seeded_colors_by_default(server_url, tmp_path, monkeypatch):  # noqa: F811
    if not OUTPUT.exists():
        pytest.skip("Private draft seeds are excluded from public releases")
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "drafts"))
    records = {}
    for arch in ["upper", "lower"]:
        correction = json.loads((OUTPUT / f"{arch}-corrections.json").read_text())
        report = json.loads((OUTPUT / f"{arch}-report.json").read_text())
        assert install(arch, correction, report)["ok"]
        records[arch] = correction
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1100})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-02")
            for arch, filename in [("upper", "progress-02-upper-clean.stl"), ("lower", "fusion-h-4.stl")]:
                if arch == "lower":
                    page.locator("#reviewLoadlower").click()
                expect(page.locator("#reviewSource")).to_contain_text(filename, timeout=60000)
                expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored automatic draft")
                expect(page.locator("#reviewChecked")).not_to_be_checked()
                expect(page.locator("#reviewCapture, #reviewUpperCapture")).to_have_count(0)
                with page.expect_download() as downloaded:
                    page.locator("#reviewExport").click()
                path = tmp_path / f"{arch}-export.json"
                downloaded.value.save_as(path)
                assert json.loads(path.read_text()) == records[arch]
                page.locator("#regionCanvas").screenshot(path=str(tmp_path / f"{arch}-seed-colors.png"))
        finally:
            browser.close()
