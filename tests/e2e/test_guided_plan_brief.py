"""Discussion goals persist separately from movements and the personal profile."""
import json
from pathlib import Path

import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def open_plan(page):
    page.locator('#guidedRail [data-gstep-nav="details"]').click()
    return page.locator("#planBriefText")


def test_goals_persist_and_stay_separate_from_sample_and_movements(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.locator("#teethProfile").click()
            notes = open_plan(page)
            before = page.locator("#planJson").input_value()
            personal = "- 11: Discuss appearance\n- <img src=x onerror=alert(1)>"
            notes.fill(personal)
            expect(page.locator("#planBriefStatus")).to_contain_text("Saved in this browser")
            assert page.locator("#planJson").input_value() == before
            page.locator('#guidedRail [data-gstep-nav="review"]').click()
            summary = page.locator('[data-gstep="review"] [data-plan-brief-summary]')
            expect(summary.locator("li")).to_have_count(2)
            expect(summary.locator("img")).to_have_count(0)
            page.reload(wait_until="networkidle")
            page.locator("#teethProfile").click()
            expect(open_plan(page)).to_have_value(personal)
            page.locator("#sampleLaunch").click()
            expected = page.request.get(server_url + "/api/sample-plan-brief").json()["text"]
            expect(open_plan(page)).to_have_value(expected)
            notes.fill("- Sample-only discussion")
            page.locator("#teethProfile").click()
            expect(open_plan(page)).to_have_value(personal)
            with page.expect_download() as pending:
                page.locator("#downloadPlanBrief").click()
            destination = tmp_path / "goals.txt"
            pending.value.save_as(destination)
            assert personal in destination.read_text()
            page.locator("#sampleLaunch").click()
            expect(open_plan(page)).to_have_value("- Sample-only discussion")
            assert not errors
        finally:
            browser.close()


def test_late_sample_response_cannot_overwrite_typed_goals_and_storage_failure_is_visible(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        pending = []
        try:
            page.route("**/api/sample-plan-brief", lambda route: pending.append(route))
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            notes = open_plan(page)
            expect(page.locator("#planBriefStatus")).to_have_text("Loading sample goals…")
            notes.fill("- Keep my current draft")
            pending.pop().fulfill(json={"ok": True, "available": True, "text": "- Older supplied goal"})
            expect(notes).to_have_value("- Keep my current draft")
            page.evaluate("() => { Storage.prototype.setItem = () => {throw new Error('full')}; }")
            notes.fill("- Unsaved revision")
            expect(page.locator("#planBriefStatus")).to_contain_text("Could not save")
            expect(page.locator("#downloadPlanBrief")).to_be_enabled()
        finally:
            browser.close()


def test_supplied_private_sample_brief_and_mobile_layout(server_url, tmp_path):  # noqa: F811
    fixture = Path(__file__).resolve().parents[2] / "datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/private/plan-brief.json"
    if not fixture.exists():
        pytest.skip("Private sample goals omitted from public snapshot")
    expected = json.loads(fixture.read_text())["text"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            page.locator("[data-plan-brief-edit]").first.click()
            expect(page.locator("#planBriefText")).to_have_value(expected)
            expect(page.locator("#samplePlanBriefCaveat")).to_be_visible()
            page.locator(".plan-brief").screenshot(path=str(tmp_path / "sample-goals.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".plan-brief").screenshot(path=str(tmp_path / "sample-goals-mobile.png"))
            assert page.locator(".plan-brief").evaluate("el => el.scrollWidth <= el.clientWidth")
        finally:
            browser.close()
