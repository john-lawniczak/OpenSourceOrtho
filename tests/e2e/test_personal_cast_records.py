"""Companion casts stay attached to week 21 without replacing dental observations."""
import hashlib
from pathlib import Path

import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


BUNDLE = Path(__file__).resolve().parents[2] / "datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/personal-models"


def assert_impression_downloads(page, base_url, impression, result):
    for index, record in enumerate(result["impressions"]):
        scan = record["captures"][0]
        response = page.request.get(base_url + impression.locator("a[download]").nth(index).get_attribute("href"))
        assert response.ok
        assert hashlib.sha256(response.body()).hexdigest() == scan["sha256"]
        photo, = record["photos"]
        link = impression.get_by_role("link", name=photo["label"], exact=True)
        expect(link).to_be_visible()
        response = page.request.get(base_url + link.get_attribute("href"))
        assert response.ok and response.headers["content-type"] == "image/png"
        assert hashlib.sha256(response.body()).hexdigest() == photo["sha256"]


def test_companion_scores_downloads_and_visit_scope(server_url, tmp_path):  # noqa: F811
    if not (BUNDLE / "summary.json").is_file():
        pytest.fail("Published companion cast bundle is missing")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="21"]').click()
            panel = page.locator("#comparisonWeek21Casts")
            expect(panel).to_be_visible(timeout=30000)
            panel.locator(":scope > summary").click()
            expect(panel).to_contain_text("Lower Model 1: 7.50/10.00")
            expect(panel).to_contain_text("held together with clay")
            expect(panel).to_contain_text("Public companion records")
            expect(panel.locator("a[download]")).to_have_count(6)
            provenance = panel.locator("#personalCaptureReview")
            provenance.locator(":scope > summary").click()
            expect(provenance).to_contain_text("3 captures of one object")
            broken = provenance.locator('[data-capture-file="lower-2-c6.stl"]')
            broken.locator("summary").click()
            expect(broken).to_contain_text("Not an intact-arch reference")
            expect(broken).to_contain_text("unverified fragment positions")
            provenance.locator(":scope > summary").click()
            result = page.request.get(server_url + "/api/sample-personal-models").json()
            for scan in result["captures"]:
                response = page.request.get(server_url + "/api/sample-personal-models/assets/" + scan["filename"])
                assert response.ok and response.headers["cache-control"] == "no-store"
                assert hashlib.sha256(response.body()).hexdigest() == scan["sha256"]
            impression = page.locator("#comparisonWeek21Impression")
            expect(impression).to_be_visible()
            impression.locator(":scope > summary").click()
            expect(impression).to_contain_text("Upper impression 1: 7.50/10.00")
            expect(impression).to_contain_text("Lower impression 1: 6.75/10.00")
            expect(impression).to_contain_text("2026-11-24")
            expect(impression).to_contain_text("negative-impression")
            expect(impression.locator("a[download]")).to_have_count(2)
            assert_impression_downloads(page, server_url, impression, result)
            impression.screenshot(path=str(tmp_path / "week-21-impression.png"))
            expect(page.locator("#comparisonVisit")).to_contain_text("exported bite coordinates", timeout=60000)
            panel.screenshot(path=str(tmp_path / "week-21-personal-casts.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator('[data-comparison-week="7"]').click()
            expect(panel).not_to_be_visible()
            expect(impression).not_to_be_visible()
            assert not errors
        finally:
            browser.close()


def test_absent_companion_bundle_does_not_block_dental_history(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.route("**/api/sample-personal-models", lambda route: route.fulfill(json={"available": False}))
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("exported bite coordinates", timeout=60000)
            expect(page.locator("#comparisonWeek21Casts")).not_to_be_visible()
            expect(page.locator("#comparisonWeek21Records")).to_be_visible()
        finally:
            browser.close()
