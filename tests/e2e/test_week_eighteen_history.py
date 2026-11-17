"""Week 18 observations stay separate from fitted weeks and existing saves."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_observed_comparison import canvas_snapshot  # noqa: E402


def reopen_week_eighteen_notes(page, editor):
    page.locator("#teethProfile").click()
    page.locator('[data-step-target="notes"]').click()
    card = page.locator('.painting-note').filter(has_text='USER_ONE · Week 18 · Lower')
    expect(card).to_contain_text('Inspect week 18 model chip tomorrow')
    card.get_by_role('link', name='Open painting & notes').click()
    expect(editor.locator("#reviewSource")).to_contain_text("week 18", timeout=60000)
    expect(editor.locator("#reviewArch")).to_have_value("lower")
    expect(editor.locator("#reviewNotes")).to_have_value("Inspect week 18 model chip tomorrow", timeout=60000)


def check_history_placement(page, requests, canvas, baseline, tmp_path):
    assert any(url.endswith("progress-02-upper-clean.stl") for url in requests)
    assert any(url.endswith("fusion-h-4.stl") for url in requests)
    assert not any(url.endswith("progress-02-upper.stl") for url in requests)
    expect(page.locator("#comparisonVisit")).to_contain_text("approximate bite display")
    canvas.evaluate("el => el.scrollIntoView({block: 'center'})")
    canvas.screenshot(path=str(tmp_path / "week-18-both.png"))
    for view in ["left", "right"]:
        page.locator(f'[data-comparison-view="{view}"]').click()
        canvas.screenshot(path=str(tmp_path / f"week-18-{view}.png"))
    page.locator('[data-comparison-view="front"]').click()
    page.locator('[data-comparison-week="1"]').click()
    assert canvas_snapshot(page.locator("#comparisonCanvas canvas"), path=str(tmp_path / "baseline-after.png")) == baseline


def test_header_toggle_button_and_lazy_week_eighteen(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "notes"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        requests, errors = [], []
        page.on("request", lambda req: requests.append(req.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            gear = page.locator("#openChatSettings")
            assert gear.bounding_box()["x"] < 400
            assert gear.evaluate("el => getComputedStyle(el).fontSize") == "14px"
            sparkle = page.locator("#topbarAskAI")
            sparkle.click()
            expect(sparkle).to_have_attribute("aria-expanded", "true")
            sparkle.click()
            expect(sparkle).to_have_attribute("aria-expanded", "false")
            expect(page.locator("#aiChatBlock")).not_to_be_visible()
            page.locator("#teethProfile").click()
            page.locator("#guidedNext").click()
            expect(page.locator(".painting-workspace-button")).to_be_visible()
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            assert not any("progress-02" in url and url.endswith(".stl") for url in requests)
            canvas = page.locator("#comparisonCanvas")
            baseline = canvas_snapshot(page.locator("#comparisonCanvas canvas"), path=str(tmp_path / "baseline-before.png"))
            page.locator('[data-comparison-week="18"]').click()
            expect(page.locator("#comparisonStatus")).to_contain_text("Week 18 observed surfaces", timeout=60000)
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "observed")
            expect(page.locator("#comparisonTooth")).to_be_disabled()
            expect(page.locator("#comparisonVisit")).to_contain_text("Acquisition date unknown")
            check_history_placement(page, requests, canvas, baseline, tmp_path)
            page.locator('[data-comparison-week="12"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "unavailable")
            expect(page.locator("#comparisonCanvas")).not_to_be_visible()
            page.locator('[data-comparison-week="4"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "estimated")
            page.locator('[data-comparison-week="18"]').click()
            page.get_by_role("link", name="Paint USER_ONE week 18 lower", exact=True).click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSource")).to_contain_text("week 18", timeout=60000)
            expect(editor.locator("#reviewArch")).to_have_value("lower")
            expect(editor.locator("#reviewSource")).to_contain_text("fusion-h-4.stl")
            expect(editor.locator("#reviewSuggestedSource")).to_contain_text("Fusion H4")
            editor.locator("#regionCanvas").screenshot(path=str(tmp_path / "week-18-lower-painting.png"))
            editor.locator("#reviewNotes").fill("Inspect week 18 model chip tomorrow")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
            expect(editor.locator("#reviewSavePath")).to_contain_text("week-18-lower")
            page.locator("#precisionBack").click()
            reopen_week_eighteen_notes(page, editor)
            page.locator("#precisionBack").click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(tmp_path / "week-18-mobile.png"))
            assert page.locator(".app-topbar").evaluate("el => el.scrollWidth <= el.clientWidth")
            assert not errors
        finally:
            browser.close()


def test_failed_week_eighteen_preserves_earlier_fit_and_retries(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.route("**/progress-02-upper-clean.stl", lambda route: route.fulfill(status=503, body="Unavailable"))
            page.locator('[data-comparison-week="18"]').click()
            expect(page.locator("#comparisonStatus")).to_contain_text("HTTP 503")
            expect(page.locator("#comparisonCanvas")).not_to_be_visible()
            page.locator('[data-comparison-week="4"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "estimated")
            page.unroute("**/progress-02-upper-clean.stl")
            page.locator('[data-comparison-week="18"]').click()
            page.locator("#comparisonRetry").click()
            expect(page.locator("#comparisonStatus")).to_contain_text("Week 18 observed surfaces", timeout=60000)
            expect(page.locator("#comparisonCanvas")).to_be_visible()
        finally:
            browser.close()


def test_clean_upper_painting_save_switch_and_reopen(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "notes"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.get_by_role("link", name="Paint USER_ONE week 18 upper", exact=True).click()
            editor = page.frame_locator(".precision-dialog iframe")
            expect(editor.locator("#reviewSource")).to_contain_text("progress-02-upper-clean.stl", timeout=60000)
            expect(editor.locator("#reviewSuggestedSource")).to_contain_text("cleaned upper")
            expect(editor.locator("#reviewCapture, #reviewUpperCapture")).to_have_count(0)
            editor.locator("#regionCanvas").screenshot(path=str(tmp_path / "clean-upper-painting.png"))
            editor.locator("#reviewNotes").fill("Clean version: inspect missing model surfaces")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSavePath")).to_contain_text("week-18-upper-upper-clean")
            editor.locator("#reviewLoadlower").click()
            expect(editor.locator("#reviewSource")).to_contain_text("fusion-h-4.stl", timeout=60000)
            expect(editor.locator("#reviewNotes")).to_have_value("")
            editor.locator("#reviewNotes").fill("Suggested lower notes")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Saved lower draft locally")
            editor.locator("#reviewLoadupper").click()
            expect(editor.locator("#reviewNotes")).to_have_value("Clean version: inspect missing model surfaces", timeout=60000)
            editor.locator("#reviewNotes").fill("Unsaved change")
            page.once("dialog", lambda dialog: dialog.dismiss())
            editor.locator("#reviewLoadlower").click()
            expect(editor.locator("#reviewSuggestedSource")).to_contain_text("cleaned upper")
            expect(editor.locator("#reviewNotes")).to_have_value("Unsaved change")
            editor.locator("#reviewSaveLocal").click()
            expect(editor.locator("#reviewSaveStatus")).to_contain_text("Saved upper draft locally")
            page.locator("#precisionBack").click()
            page.locator("#teethProfile").click()
            page.locator('[data-step-target="notes"]').click()
            card = page.locator('.painting-note').filter(has_text='USER_ONE · Week 18 · Upper · Cleaned version')
            card.get_by_role('link', name='Open painting & notes').click()
            expect(editor.locator("#reviewSource")).to_contain_text("progress-02-upper-clean.stl", timeout=60000)
            expect(editor.locator("#reviewNotes")).to_have_value("Unsaved change", timeout=60000)
            assert not errors
        finally:
            browser.close()


def test_week_eighteen_single_arch_and_original_h4_fallback(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.route("**/api/sample-history/lower-cleaned", lambda route: route.fulfill(
                content_type="application/json", body='{"available":false}'))
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="18"]').click()
            expect(page.locator("#comparisonStatus")).to_contain_text("original H4 lower", timeout=60000)
            for arch, description in [("upper", "cleaned upper"), ("lower", "original H4 lower")]:
                page.locator(f'[data-comparison-arch="{arch}"]').click()
                expect(page.locator("#comparisonStatus")).to_contain_text(description, timeout=60000)
                expect(page.locator("#sampleComparison")).to_have_attribute("data-frame-kind", "observed")
                page.locator("#comparisonCanvas").screenshot(path=str(tmp_path / f"week-18-{arch}.png"))
            assert not errors
        finally:
            browser.close()
