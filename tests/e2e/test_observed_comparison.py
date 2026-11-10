"""Real sample observations stay separate from simulated planning stages."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def assert_observed_endpoints_preserve_camera(page, tmp_path):
    canvas = page.locator("#comparisonCanvas canvas")
    page.locator("#comparisonZoomIn").click()
    page.locator("#comparisonBaseline").click()
    baseline = canvas.screenshot(path=str(tmp_path / "observed-baseline.png"))
    page.locator("#comparisonWeek7").click()
    progress = canvas.screenshot(path=str(tmp_path / "observed-week7.png"))
    assert baseline != progress, "Endpoints must show different observed surfaces"
    page.locator("#comparisonBaseline").click()
    assert canvas.screenshot() == baseline, "Scrubbing must preserve camera and original geometry"


def test_observed_pair_reveal_camera_arch_and_personal_state(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonBefore")).to_contain_text("Week 1 / baseline")
            expect(page.locator("#comparisonValidation")).to_contain_text("validated, confirmed by the contributor")
            expect(page.locator("#comparisonAfter")).to_contain_text("Reported week 7")
            expect(page.locator("#stageSlider")).not_to_be_visible()
            expect(page.locator("#guidedBuild")).not_to_be_visible()
            expect(page.locator("#chatReopenTab")).not_to_be_visible()
            expect(page.locator("#comparisonReveal")).to_have_value("50")
            canvas = page.locator("#comparisonCanvas canvas")
            assert_observed_endpoints_preserve_camera(page, tmp_path)
            count_before = len([url for url in requests if url.endswith(".stl")])
            page.locator("#comparisonReveal").focus()
            page.locator("#comparisonReveal").press("ArrowRight")
            expect(page.locator("#comparisonReveal")).to_have_value("0.1")
            page.locator("#comparisonSplit").click()
            expect(page.locator("#comparisonDivider")).to_be_visible()
            handle = page.locator("#comparisonDivider").bounding_box()
            page.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
            page.mouse.down()
            page.mouse.move(handle["x"] + 100, handle["y"] + handle["height"] / 2, steps=5)
            page.mouse.up()
            assert float(page.locator("#comparisonReveal").input_value()) < 50
            assert len([url for url in requests if url.endswith(".stl")]) == count_before
            page.locator("#comparisonArch").select_option("lower")
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            assert any(url.endswith("progress-01-lower.stl") for url in requests)
            assert not any("progress-02" in url for url in requests)
            page.locator("#comparisonBaseline").click()
            box = canvas.bounding_box()
            canvas.dblclick(position={"x": box["width"] * 0.5, "y": box["height"] * 0.75})
            expect(page.locator("#comparisonStatus")).to_contain_text("Region focused")
            page.locator("#comparisonReset").click()
            page.locator("#comparisonSplit").click()
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "observed-desktop.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            expect(canvas).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "observed-mobile.png"))
            page.locator("#sampleExit").click()
            expect(page.locator("#sampleComparison")).not_to_be_visible()
            expect(page.locator("#comparisonCanvas canvas")).to_have_count(0)
            expect(page.locator("#simpleStlFile")).to_be_enabled()
            expect(page.locator("#chatReopenTab")).to_be_visible()
            assert not errors
        finally:
            browser.close()


def test_failed_visit_does_not_display_partial_pair_and_can_retry(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.route("**/progress-01-upper.stl", lambda route: route.fulfill(status=503, body="unavailable"))
            page.goto(server_url, wait_until="networkidle")
            page.locator("#sampleLaunch").click()
            expect(page.locator("#comparisonStatus")).to_contain_text("Comparison unavailable", timeout=30000)
            expect(page.locator("#comparisonReveal")).to_be_disabled()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "false")
            page.unroute("**/progress-01-upper.stl")
            page.locator("#comparisonRetry").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            page.locator('[data-sample-view="simulation"]').click()
            expect(page.locator("#sampleComparison")).not_to_be_visible()
            expect(page.locator("#sampleSimulationNote")).to_be_visible()
            expect(page.locator("#stageSlider")).to_be_visible()
            page.locator('[data-sample-view="observed"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#stageSlider")).not_to_be_visible()
        finally:
            browser.close()
