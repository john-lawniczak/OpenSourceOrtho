"""Real sample observations stay separate from simulated planning stages."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def canvas_snapshot(canvas, **kwargs):
    # Rounded CSS corners can differ by 1–2 RGB levels after browser scrolling.
    # Remove that border mask for exact comparison of the rendered scan pixels.
    return canvas.screenshot(style=".comparison-stage { border-radius: 0 !important; } .comparison-visit { visibility: hidden !important; }", **kwargs)


def assert_observed_endpoints_preserve_camera(page, tmp_path):
    canvas = page.locator("#comparisonCanvas canvas")
    page.locator("#comparisonZoomIn").click()
    page.locator('[data-comparison-week="1"]').click()
    baseline = canvas_snapshot(canvas, path=str(tmp_path / "observed-baseline.png"))
    page.locator('[data-comparison-week="7"]').click()
    progress = canvas_snapshot(canvas, path=str(tmp_path / "observed-week7.png"))
    assert baseline != progress, "Endpoints must show different observed surfaces"
    page.locator('[data-comparison-week="1"]').click()
    assert canvas_snapshot(canvas) == baseline, "Changing weeks must preserve camera and original geometry"


def assert_week_navigation(page, canvas, requests, count_before, tmp_path):
    baseline = canvas_snapshot(canvas, path=str(tmp_path / "before-weeks.png"))
    frames = []
    for week in range(2, 7):
        page.locator("#comparisonNext").click()
        expect(page.locator("#comparisonWeekLabel")).to_have_text(f"Week {week} of 7")
        expect(page.locator("#comparisonMissing")).not_to_be_visible()
        expect(canvas).to_be_visible()
        expect(page.locator("#comparisonVisit")).to_contain_text("SIMULATED ESTIMATE")
        expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "estimated")
        frames.append(canvas_snapshot(canvas))
    assert len(set(frames)) == 5, "Every intermediate week must render a distinct fitted pose"
    page.locator("#sampleComparison").screenshot(path=str(tmp_path / "estimated-week6.png"))
    page.locator("#comparisonNext").click()
    expect(page.locator("#comparisonVisit")).to_contain_text("Reported week 7")
    expect(page.locator("#comparisonNext")).to_be_disabled()
    recorded = canvas_snapshot(canvas)
    page.locator("#comparisonEndpointFit").click()
    expect(page.locator("#comparisonVisit")).to_contain_text("SIMULATED ESTIMATE")
    assert canvas_snapshot(canvas) != recorded
    page.locator("#comparisonEndpointFit").click()
    assert canvas_snapshot(canvas) == recorded
    expect(page.locator("#comparisonMissing")).not_to_be_visible()
    page.locator('[data-comparison-week="1"]').click()
    assert canvas_snapshot(canvas, path=str(tmp_path / "after-weeks.png")) == baseline
    page.locator('[data-comparison-week="7"]').focus()
    page.keyboard.press("Enter")
    expect(page.locator('[data-comparison-week="7"]')).to_have_attribute("aria-current", "step")
    assert len([url for url in requests if url.endswith(".stl")]) == count_before


def test_observed_history_camera_arch_and_personal_state(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        try:
            page.goto(server_url, wait_until="networkidle")
            expect(page.locator("#uploadIntroduction")).to_have_count(0)
            expect(page.locator("#segmentationBlock")).not_to_be_visible()
            page.locator("#guidedNext").click()
            expect(page.locator("#segmentationBlock")).to_be_visible()
            page.locator("#sampleLaunch").click()
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            expect(page.locator("#comparisonVisit")).to_contain_text("Week 1 / baseline")
            expect(page.locator(".comparison-provenance")).to_have_count(0)
            expect(page.locator("#comparisonPrevious")).to_be_disabled()
            expect(page.locator("#stageSlider")).not_to_be_visible()
            expect(page.locator("#guidedBuild")).not_to_be_visible()
            expect(page.locator("#chatReopenTab")).not_to_be_visible()
            canvas = page.locator("#comparisonCanvas canvas")
            assert_observed_endpoints_preserve_camera(page, tmp_path)
            count_before = len([url for url in requests if url.endswith(".stl")])
            assert_week_navigation(page, canvas, requests, count_before, tmp_path)
            page.locator("#comparisonReset").click()
            page.locator("#sampleComparison").screenshot(path=str(tmp_path / "upper-front.png"))
            page.locator('[data-comparison-arch="lower"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=30000)
            assert any(url.endswith("progress-01-lower.stl") for url in requests)
            assert not any("progress-02" in url for url in requests)
            page.locator('[data-comparison-week="1"]').click()
            page.locator('[data-comparison-view="occlusal"]').click()
            box = canvas.bounding_box()
            canvas.dblclick(position={"x": box["width"] * 0.5, "y": box["height"] * 0.8125})
            expect(page.locator("#comparisonStatus")).to_contain_text("Region focused")
            page.locator("#comparisonReset").click()
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
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#comparisonStatus")).to_contain_text("Comparison unavailable", timeout=30000)
            expect(page.locator("#comparisonNext")).to_be_disabled()
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
