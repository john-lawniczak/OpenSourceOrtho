"""Discoverable baseline labeling, controls, and durable local saves."""
import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


@pytest.fixture
def review_page(server_url, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "snapshots"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        yield page
        browser.close()


def test_discovery_arch_switch_and_visual_controls(review_page, server_url, tmp_path):  # noqa: F811
    page = review_page
    page.goto(server_url)
    page.get_by_role("link", name="Paint tooth boundaries Step 2 · Identify teeth").click()
    expect(page.locator(".review-workflow")).to_contain_text("Step 2")
    expect(page.locator("#reviewArch")).to_have_value("")
    expect(page.locator("#reviewOtherColors")).to_be_checked()
    expect(page.locator("#reviewShowLabel")).not_to_be_checked()
    page.locator("#reviewLoadlower").click()
    expect(page.locator("#reviewSource")).to_contain_text("initial-lower.stl", timeout=30000)
    expect(page.locator('[data-tooth="18"]')).to_have_count(0)
    expect(page.locator('[data-tooth="28"]')).to_have_count(0)
    page.locator("#reviewFocus").click()
    expect(page.locator("#reviewSelectionMarker")).to_be_hidden()
    page.locator("#reviewShowLabel").check()
    expect(page.locator("#reviewSelectionMarker")).to_be_visible()
    page.locator("#reviewShowLabel").uncheck()
    expect(page.locator("#reviewSelectionMarker")).to_be_hidden()
    page.locator("#reviewShowLabel").check()
    canvas = page.locator("#regionCanvas canvas")
    before = canvas.screenshot()
    page.locator("#reviewZoomIn").click()
    assert canvas.screenshot() != before
    page.locator("#reviewZoomOut").click()
    page.locator("#reviewBrushLarger").click()
    expect(page.locator("#reviewRadius")).to_have_value("1.1")
    page.keyboard.press("BracketRight")
    expect(page.locator("#reviewRadius")).to_have_value("1.2")
    page.keyboard.press("BracketLeft")
    expect(page.locator("#reviewRadius")).to_have_value("1.1")
    page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
    page.locator("#reviewNotes").fill("Notes [ and ] are text")
    page.locator("#reviewNotes").press("BracketRight")
    expect(page.locator("#reviewRadius")).to_have_value("1.1")
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
    page.locator("#reviewLoadupper").click()
    expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
    expect(page.locator('[data-tooth="18"]')).to_be_visible()
    expect(page.locator('[data-tooth="31"]')).to_have_count(0)
    page.screenshot(path=str(tmp_path / "upper-baseline-controls.png"), full_page=True)


def test_both_baselines_resume_separate_versioned_labels(review_page, server_url, tmp_path):  # noqa: F811
    page = review_page
    page.goto(server_url + "/region-review.html?baseline=lower")
    expect(page.locator("#reviewSource")).to_contain_text("initial-lower.stl", timeout=30000)
    page.get_by_text("Split / merge labels", exact=True).click()
    page.locator("#reviewMerge").click()
    page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
    page.locator("#reviewNotes").fill("Lower notes: uncertain chip position")
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
    lower_path = next((tmp_path / "snapshots/USER_ONE/baseline-lower").glob("*.json"))
    saved_lower = json.loads(lower_path.read_text())
    page.locator("#reviewLoadupper").click()
    expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
    page.locator("#reviewChecked").check()
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper user-reviewed locally")
    page.reload()
    expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
    expect(page.locator("#reviewChecked")).to_be_checked()
    page.locator("#reviewLoadlower").click()
    expect(page.locator("#reviewSource")).to_contain_text("initial-lower.stl", timeout=30000)
    expect(page.locator("#reviewNotes")).to_have_value("Lower notes: uncertain chip position")
    expect(page.locator("#reviewChecked")).not_to_be_checked()
    with page.expect_download() as download:
        page.locator("#reviewExport").click()
    exported = tmp_path / "restored.json"
    download.value.save_as(exported)
    assert json.loads(exported.read_text()) == saved_lower["corrections"]
    page.locator("#reviewLoadupper").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored user-reviewed", timeout=30000)
    expect(page.locator("#reviewChecked")).to_be_checked()
    assert len(list((tmp_path / "snapshots").rglob("*.json"))) == 2
    page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
    page.locator("#reviewNotes").fill("Upper second version")
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper user-reviewed locally")
    assert len(list((tmp_path / "snapshots").rglob("*.json"))) == 3
    assert json.loads(Path(lower_path).read_text()) == saved_lower


def test_reload_saved_gets_new_numbers_and_stale_save_is_rejected(review_page, server_url, tmp_path):  # noqa: F811
    from orthoplan.region_corrections import save_baseline_corrections
    import base64
    page = review_page
    page.goto(server_url + "/region-review.html?baseline=upper")
    expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally")
    original = page.request.get(server_url + "/api/region-corrections/upper")
    assert original.headers["cache-control"] == "no-store"
    record = original.json()["corrections"]
    record["labels_base64"] = base64.b64encode(bytes([22]) * record["face_count"]).decode()
    saved = save_baseline_corrections({"arch": "upper", "corrections": record}, root=tmp_path / "snapshots")
    assert saved["ok"]
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("A newer draft is saved")
    page.locator("#reviewReload").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored draft")
    expect(page.locator('[data-tooth="18"]')).to_be_disabled()
    page.locator('[data-tooth="17"]').click()
    expect(page.locator("#reviewSelectionHelp")).to_contain_text("No surface is labeled 17")
    page.locator('[data-tooth="22"]').click()
    expect(page.locator("#reviewSelectionHelp")).to_contain_text(f'{record["face_count"]:,} labeled faces')
