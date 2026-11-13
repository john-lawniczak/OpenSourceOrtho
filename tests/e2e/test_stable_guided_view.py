"""The teeth remain above step information without resetting the user's camera."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface  # noqa: E402


def test_shared_view_stays_above_content_and_keeps_camera(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1300})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.locator("#teethProfile").click()
            expect(page.locator("#guidedViewerHost")).to_be_hidden()
            page.locator("#simpleStlFile").set_input_files(surface(tmp_path))
            expect(page.locator("#viewerBlock .scan-view-controls")).to_be_visible()
            canvas = page.locator("#viewer3d canvas")
            canvas.evaluate("el => { window.originalGuidedCanvas = el; }")
            default = canvas.screenshot()
            page.locator('[data-scan-view="roll-right"]').click()
            page.locator("#zoomIn").click()
            page.mouse.move(0, 0)  # Avoid capturing the zoom button's hover style.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            adjusted = canvas.screenshot(path=str(tmp_path / "adjusted.png"))
            assert adjusted != default
            tops = []
            for step in ["plan", "details", "review", "preview", "print", "upload"]:
                page.locator(f'#guidedRail [data-gstep-nav="{step}"]').click()
                page.evaluate("window.scrollTo(0, 0)")
                host = page.locator("#guidedViewerHost")
                heading = page.locator(f'.gstep[data-gstep="{step}"] > h3')
                assert heading.bounding_box()["y"] >= host.bounding_box()["y"] + host.bounding_box()["height"]
                tops.append(host.bounding_box()["y"])
                assert canvas.evaluate("el => el === window.originalGuidedCanvas")
                page.wait_for_timeout(100)
                assert canvas.screenshot(path=str(tmp_path / f"{step}.png")) == adjusted, f"Camera changed on {step}"
            assert max(tops) - min(tops) <= 1
            expect(page.locator('#guidedRail [data-gstep-nav="plan"]')).to_contain_text("Explore your teeth")
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            page.locator("#planBriefText").fill("- Discuss the selected tooth")
            page.locator("#planBriefText").scroll_into_view_if_needed()
            page.locator('#guidedRail [data-gstep-nav="review"]').click()
            expect(page.locator("#guidedViewerHost")).to_be_in_viewport()
            expect(page.locator("#guidedViewerDetailsHost")).to_be_hidden()
            assert not errors
        finally:
            browser.close()


def test_sample_plan_view_layout_and_mobile_notes(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            summary = page.locator('.gstep[data-gstep="plan"] .plan-brief-summary')
            assert summary.bounding_box()["y"] > page.locator("#comparisonCanvas").bounding_box()["y"]
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(page.locator("#sampleReloadPainting")).to_be_enabled(timeout=90000)
            expect(page.locator("#scanRenderStatus")).to_contain_text("Showing your scan", timeout=60000)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(tmp_path / "plan-view-first.png"))
            page.locator("#viewer3d").scroll_into_view_if_needed()
            page.screenshot(path=str(tmp_path / "plan-teeth-and-notes.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("#guidedViewerHost")).to_have_css("position", "static")
            notes = page.locator("#planBriefText")
            notes.fill("- Mobile draft stays editable beneath the teeth")
            notes.scroll_into_view_if_needed()
            expect(notes).to_be_in_viewport()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "plan-notes-mobile.png"))
            page.locator('#guidedRail [data-gstep-nav="preview"]').click()
            page.locator('#guidedRail [data-gstep-nav="details"]').click()
            expect(notes).to_have_value("- Mobile draft stays editable beneath the teeth")
        finally:
            browser.close()
