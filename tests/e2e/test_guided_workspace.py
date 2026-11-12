"""Viewer-first navigation and constrained sidebar regressions."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_settings_and_phase_navigation_stay_in_place(server_url):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(server_url, wait_until="networkidle")
            expect(page.locator('.sidebar [data-user-mode]')).to_have_count(0)
            expect(page.locator('.app-topbar #openChatSettings')).to_be_visible()
            for step in ['plan', 'details', 'review', 'preview', 'plan']:
                page.evaluate('window.scrollTo(0, 0)')
                page.locator(f'[data-gstep-nav="{step}"]').click()
                expect(page.locator(f'.gstep[data-gstep="{step}"]')).to_be_visible()
                assert page.evaluate('window.scrollY') == 0
            page.locator('#sampleLaunch').click()
            page.locator('[data-sample-view="simulation"]').click()
            page.locator('#openChatSettings').click()
            page.locator('[data-user-mode="advanced"]').click()
            expect(page.locator('#chatSettingsDialog')).not_to_be_visible()
            page.locator('#anatomyPanel > summary').click()
            page.wait_for_selector('.anatomy-actions')
            assert page.locator('.sidebar').evaluate('el => el.scrollWidth <= el.clientWidth')
            for width in [1200, 390]:
                page.set_viewport_size({"width": width, "height": 900})
                assert page.locator('.sidebar').evaluate('el => el.scrollWidth <= el.clientWidth')
        finally:
            browser.close()
