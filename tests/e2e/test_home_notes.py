"""Clean home, illustrative examples and accessible saved note discovery."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_home_examples_preserve_plan_and_workflow_access(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until="networkidle")
            expect(page.locator('.gstep[data-gstep="upload"]')).to_be_visible()
            expect(page.locator("#guidedRail")).to_be_visible()
            expect(page.locator("#teethProfile")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#toothExplorer")).to_be_hidden()
            expect(page.locator('[data-step-target="toothmap"]')).to_have_text("Tooth Map")
            page.locator('[data-step-target="toothmap"]').click()
            expect(page.locator("#toothExplorer")).to_be_visible()
            for selector in ["#guided", "#guidedRail", ".sidebar > .review-tier-panel", "#chatReopenTab"]:
                for item in page.locator(selector).all():
                    expect(item).not_to_be_visible()
            before = page.locator("#planJson").input_value()
            page.locator('#toothExplorerGrid [data-fdi="31"]').click()
            canvas = page.locator("#toothExplorerViewer canvas")
            expect(canvas).to_be_visible()
            images = []
            for example in ["crowding", "spacing", "open-bite", "neutral"]:
                page.locator(f'[data-tooth-example="{example}"]').click()
                expect(page.locator(f'[data-tooth-example="{example}"]')).to_have_attribute("aria-pressed", "true")
                expect(page.locator('#toothExplorerGrid [data-fdi="31"]')).to_have_attribute("aria-pressed", "true")
                canvas.evaluate("el => el.scrollIntoView({block: 'center'})")
                page.wait_for_timeout(100)
                images.append(canvas.screenshot(path=str(tmp_path / f"example-{example}.png")))
                assert page.locator("#planJson").input_value() == before
            assert len(set(images)) == 4
            page.screenshot(path=str(tmp_path / "home.png"), full_page=True)
            page.locator('#panel-toothmap [data-info-back]').click()
            expect(page.locator("#guidedRail")).to_be_visible()
            expect(page.locator('.gstep[data-gstep="upload"]')).to_be_visible()
            page.locator('[data-step-target="toothmap"]').click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "home-mobile.png"), full_page=True)
            assert not errors
        finally:
            browser.close()


def test_notes_partial_failure_and_safe_rendering(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url)
            page.route("**/api/painting-notes", lambda route: route.fulfill(status=503))
            page.evaluate('''async () => {
              const { caseStore } = await import('/progress_case_store.js');
              await caseStore('put', {name:'boundary-test-lower', scan:{filename:'lower.stl', arch:'lower'},
                notes:'<img src=x onerror=alert(1)>', saved_at:'2026-11-12T12:00:00Z'}, 'edits');
              await caseStore('put', {name:'transfer-test', notes:'Unsaved transfer'}, 'edits');
            }''')
            page.locator('[data-step-target="notes"]').click()
            expect(page.locator("#paintingNotesStatus")).to_contain_text("Could not load notes on this computer")
            expect(page.locator(".painting-note")).to_have_count(1)
            expect(page.locator(".painting-note pre")).to_have_text("<img src=x onerror=alert(1)>")
            expect(page.locator(".painting-note img")).to_have_count(0)
            expect(page.locator(".painting-note a")).to_have_attribute("href", "./region-review.html?edit=boundary-test-lower")
            page.unroute("**/api/painting-notes")
            page.route("**/api/painting-notes", lambda route: route.fulfill(json={"entries": [], "errors": []}))
            page.locator("#refreshPaintingNotes").click()
            expect(page.locator("#paintingNotesStatus")).to_have_text("1 saved painting.")
        finally:
            browser.close()
