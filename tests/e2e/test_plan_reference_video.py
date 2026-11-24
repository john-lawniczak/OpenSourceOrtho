"""The intended-plan video belongs only to the sample and stays separate from scans."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_sample_video_playback_and_exit(server_url, tmp_path):  # noqa: F811 - pytest fixture
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            reference = page.locator("#samplePlanReference")
            reference.locator("summary").click()
            expect(reference).to_contain_text("separate from observed scans")
            video = reference.locator("video")
            source = reference.locator("source").get_attribute("src")
            response = page.request.get(server_url + source)
            assert response.status == 200
            assert response.headers["content-type"] == "video/mp4"
            video.evaluate("video => video.play()")
            page.wait_for_function("document.querySelector('#samplePlanReference video').currentTime > 0")
            assert video.evaluate("video => video.duration") == pytest.approx(19.5)
            page.set_viewport_size({"width": 390, "height": 844})
            reference.screenshot(path=str(tmp_path / "plan-reference-mobile.png"))
            assert video.bounding_box()["width"] <= 390
            page.locator("#sampleExit").click()
            expect(reference).not_to_be_visible()
            assert video.evaluate("video => video.paused")
            assert not errors
        finally:
            browser.close()
