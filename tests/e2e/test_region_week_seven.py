"""Week 7 painting binds saves to the observed visit without changing week 1."""
import base64
import json

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect  # noqa: E402
from test_region_baseline_workflow import review_page, server_url  # noqa: E402,F401


def test_week_seven_paint_save_reload_and_visit_switch(review_page, server_url, tmp_path):  # noqa: F811
    page = review_page
    page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-01")
    expect(page.locator("#reviewSource")).to_contain_text("progress-01-upper.stl", timeout=30000)
    expect(page.locator("#reviewVisit")).to_have_value("progress-01")
    expect(page.locator("#reviewSaveStatus")).to_contain_text("unpainted original surface")
    expect(page.locator("#reviewSaveLocal")).to_be_enabled()
    expect(page.locator('[data-tooth="31"]')).to_have_count(0)
    page.locator('[data-tooth="11"]').click()
    page.get_by_role("button", name="Paint tooth", exact=True).click()
    canvas = page.locator("#regionCanvas canvas").bounding_box()
    # Sweep across the rendered original arch to exercise real brush hit testing.
    page.mouse.move(canvas["x"] + canvas["width"] * 0.2, canvas["y"] + canvas["height"] * 0.5)
    page.mouse.down()
    page.mouse.move(canvas["x"] + canvas["width"] * 0.8, canvas["y"] + canvas["height"] * 0.5, steps=30)
    page.mouse.up()
    page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
    page.locator("#reviewNotes").fill("Week 7 test draft")
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally")
    path = next((tmp_path / "snapshots/USER_ONE/week-7-upper").glob("*.json"))
    saved = json.loads(path.read_text())
    assert saved["visit"] == "progress-01"
    assert 11 in base64.b64decode(saved["corrections"]["labels_base64"])
    assert not saved["corrections"]["reviewed"]
    page.reload()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored draft", timeout=30000)
    expect(page.locator("#reviewNotes")).to_have_value("Week 7 test draft")
    page.locator("#reviewLoadlower").click()
    expect(page.locator("#reviewSource")).to_contain_text("progress-01-lower.stl", timeout=30000)
    expect(page.locator('[data-tooth="11"]')).to_have_count(0)
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
    assert len(list((tmp_path / "snapshots/USER_ONE/week-7-lower").glob("*.json"))) == 1
    page.locator("#reviewVisit").select_option("initial")
    expect(page.locator("#reviewSource")).to_contain_text("initial-lower.stl", timeout=30000)
    expect(page.locator("#reviewNotes")).to_have_value("")
    page.locator("#reviewSaveDetails").evaluate("el => el.open = true")
    page.locator("#reviewNotes").fill("Unsaved week 1 notes")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("#reviewVisit").select_option("progress-01")
    expect(page.locator("#reviewVisit")).to_have_value("initial")
    expect(page.locator("#reviewSource")).to_contain_text("initial-lower.stl")
    expect(page.locator("#reviewNotes")).to_have_value("Unsaved week 1 notes")
    assert not (tmp_path / "snapshots/USER_ONE/baseline-lower").exists()


def test_automatic_week_seven_draft_is_visible_and_preserved(review_page, server_url, tmp_path):  # noqa: F811
    from orthoplan.region_corrections import baseline_source, save_baseline_corrections
    source = baseline_source("upper", "progress-01")
    correction = {"schema": "ortho-region-corrections-v1", "arch": "upper",
                  "source_sha256": source["sha256"], "face_count": source["face_count"],
                  "labels_base64": base64.b64encode(bytes([11]) + bytes(source["face_count"] - 1)).decode(),
                  "provenance": "automatic-draft", "reviewed": False}
    result = save_baseline_corrections({"arch": "upper", "visit": "progress-01", "corrections": correction},
                                       root=tmp_path / "snapshots")
    assert result["ok"]
    page = review_page
    page.goto(server_url + "/region-review.html?baseline=upper&visit=progress-01")
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored automatic draft", timeout=30000)
    expect(page.locator("#reviewChecked")).not_to_be_checked()
    page.locator("#reviewSaveLocal").click()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally")
    page.reload()
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Restored automatic draft", timeout=30000)
