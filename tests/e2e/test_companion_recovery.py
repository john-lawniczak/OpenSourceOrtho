"""Failed companion loads remain visible and can recover without a page reload."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


@pytest.mark.parametrize("failure", ["http", "render"])
def test_companion_load_can_retry_and_is_scoped_to_week_21(server_url, failure):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        attempts = []

        def respond(route):
            attempts.append(True)
            if len(attempts) > 1:
                route.continue_()
            elif failure == "http":
                route.fulfill(status=503, json={"error": "temporarily unavailable"})
            else:
                route.fulfill(json={"available": True, "impressions": [{"label": "incomplete"}]})

        page.route("**/api/sample-personal-models", respond)
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#companionLoadNotice")).to_be_visible(timeout=30000)
            expect(page.locator("#companionLoadNotice")).to_contain_text("could not be loaded")
            expect(page.locator("#comparisonWeek21Records")).to_be_visible()
            page.locator('[data-comparison-week="7"]').click()
            expect(page.locator("#companionLoadNotice")).not_to_be_visible()
            page.locator('[data-comparison-week="21"]').click()
            expect(page.locator("#companionLoadNotice")).to_be_visible()
            assert len(attempts) == 1
            page.locator("#retryCompanionRecords").click()
            expect(page.locator("#comparisonWeek21Impression")).to_be_visible(timeout=30000)
            expect(page.locator("#comparisonWeek21Casts")).to_be_visible()
            expect(page.locator("#companionLoadNotice")).not_to_be_visible()
            assert len(attempts) == 2
            page.locator('[data-comparison-week="7"]').click()
            expect(page.locator("#comparisonWeek21Impression")).not_to_be_visible()
            expect(page.locator("#companionLoadNotice")).not_to_be_visible()
        finally:
            browser.close()
