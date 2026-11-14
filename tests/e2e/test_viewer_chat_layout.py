"""Chat layout changes resize the 3D canvas without changing the user's view."""
import io

import pytest

pytest.importorskip("playwright.sync_api")
from PIL import Image, ImageChops  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def assert_canvas_fills_viewer(page):
    page.wait_for_function("""() => {
        const host = document.querySelector('#viewer3d');
        const canvas = host.querySelector('canvas');
        return canvas && Math.abs(canvas.clientWidth - host.clientWidth) <= 1
            && Math.abs(canvas.clientHeight - host.clientHeight) <= 1
            && Math.abs(canvas.width - host.clientWidth * devicePixelRatio) <= 1;
    }""")


@pytest.mark.parametrize("pixel_ratio", [1, 2])
def test_chat_toggle_keeps_canvas_fitted_and_preserves_view(server_url, pixel_ratio):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1800, "height": 1200},
                                device_scale_factor=pixel_ratio)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            page.locator('[data-gstep-nav="details"]').click()
            expect(page.locator("#sampleReloadPainting")).to_be_enabled(timeout=90000)
            canvas = page.locator("#viewer3d canvas")
            expect(canvas).to_be_visible()
            page.wait_for_load_state("networkidle")
            assert_canvas_fills_viewer(page)
            before = Image.open(io.BytesIO(canvas.screenshot())).convert("RGB")
            original_width = canvas.bounding_box()["width"]
            for _ in range(2):
                page.locator("#topbarAskAI").click()
                expect(page.locator("#aiChatBlock")).to_be_visible()
                assert_canvas_fills_viewer(page)
                assert canvas.bounding_box()["width"] < original_width
                page.locator("#expandChat").click()
                assert_canvas_fills_viewer(page)
                page.locator("#expandChat").click()
                assert_canvas_fills_viewer(page)
                page.locator("#toggleChatPanel").click()
                expect(page.locator("#aiChatBlock")).not_to_be_visible()
                assert_canvas_fills_viewer(page)
                assert canvas.bounding_box()["width"] == original_width
            after = Image.open(io.BytesIO(canvas.screenshot())).convert("RGB")
            assert ImageChops.difference(before, after).getbbox() is None
            assert not errors
        finally:
            browser.close()
