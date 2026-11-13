"""Explicit note tags add focus teeth without authoring movements or crossing plans."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def open_personal_plan(page):
    page.locator("#teethProfile").click()
    page.locator('#guidedRail [data-gstep-nav="details"]').click()


def test_note_tags_add_to_saved_focus_and_stay_scoped(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        # Synthetic defaults keep this test independent of unpublished case notes.
        page.route("**/api/sample-plan-brief", lambda route: route.fulfill(json={
            "ok": True, "available": True, "text": "", "focus_teeth": ["12", "22", "31"],
        }))
        try:
            page.goto(server_url, wait_until="networkidle")
            open_personal_plan(page)
            focus = page.locator("#focusTeethInput")
            focus.fill("11")
            page.get_by_role("button", name="Save highlighted teeth").click()
            before = page.locator("#planJson").input_value()
            notes = page.locator("#planBriefText")
            notes.fill("Focus on @12 and @22. Repair #31. Repeat @12; ignore @123 and ordinary 41.")
            expect(focus).to_have_value("11, 12, 22, 31")
            expect(page.locator("#focusTeethToggle")).to_have_attribute("aria-checked", "false")
            assert page.locator("#planJson").input_value() == before
            notes.fill("Only ordinary tooth numbers: 12 and 22")
            notes.blur()
            expect(focus).to_have_value("11, 12, 22, 31")
            page.reload(wait_until="networkidle")
            open_personal_plan(page)
            expect(focus).to_have_value("11, 12, 22, 31")
            page.locator("#sampleLaunch").click()
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(focus).to_have_value("12, 22, 31", timeout=60000)
            notes.fill("Also discuss @13")
            notes.blur()
            expect(focus).to_have_value("12, 22, 31, 13")
            open_personal_plan(page)
            expect(focus).to_have_value("11, 12, 22, 31")
        finally:
            browser.close()


def test_note_typing_completion_blur_and_storage_failure(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url, wait_until="networkidle")
            open_personal_plan(page)
            notes, focus = page.locator("#planBriefText"), page.locator("#focusTeethInput")
            notes.press_sequentially("Ignore @123", delay=50)
            page.wait_for_timeout(500)  # Let the note-tag debounce finish.
            expect(focus).to_have_value("")
            focus.fill("14")  # Keep an unfinished manual list edit when a tag arrives.
            notes.fill("Discuss #22")
            notes.blur()
            expect(focus).to_have_value("14, 22")
            page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('full'); }; }")
            notes.fill("Discuss #22 and @31")
            notes.blur()
            expect(focus).to_have_value("14, 22, 31")
            expect(page.locator("#focusTeethStatus")).to_contain_text("could not be saved")
            expect(page.locator("#planBriefStatus")).to_contain_text("Could not save")
        finally:
            browser.close()
