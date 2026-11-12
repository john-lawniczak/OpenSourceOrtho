"""Progressive disclosure preserves access to secondary workflows."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: F401,E402


def test_optional_workflows_start_collapsed_and_links_reveal_controls(server_url, tmp_path):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(server_url, wait_until="networkidle")
            page.locator("#openChatSettings").click()
            page.get_by_role("button", name="Technician", exact=True).click()
            expect(page.get_by_text("Additional records · optional", exact=True)).to_be_visible()
            expect(page.locator("#recordNote")).not_to_be_visible()
            page.get_by_text("Additional records · optional", exact=True).click()
            expect(page.locator("#recordNote")).to_be_visible()
            page.locator('button[data-step="review"]').click()
            expect(page.locator("#generatePlan")).to_be_visible()
            expect(page.locator("#saveVersion")).not_to_be_visible()
            expect(page.locator("#proposeSegment")).not_to_be_visible()
            expect(page.locator("#planJson")).not_to_be_visible()
            page.locator(".viewer-diagnostics > summary").click()
            # Trust-strip links expose the requested section before navigation.
            page.locator('a[href="#segmentList"]').first.click()
            expect(page.locator("#proposeSegment")).to_be_visible()
            page.get_by_text("Saved versions", exact=True).click()
            expect(page.locator("#saveVersion")).to_be_visible()
            page.get_by_text("Technical output", exact=True).click()
            expect(page.locator("#planJson")).to_be_visible()
            page.screenshot(path=str(tmp_path / "technician-review.png"), full_page=True)
            assert not errors
        finally:
            browser.close()
