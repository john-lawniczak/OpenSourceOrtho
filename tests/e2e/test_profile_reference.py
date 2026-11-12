"""Mode confirmation, persistent navigation and organized reference tools."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_mode_confirmation_reference_layout_and_provider_choices(server_url, tmp_path):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until="networkidle")
            page.locator("#openChatSettings").click()
            page.once("dialog", lambda dialog: dialog.dismiss())
            page.locator('[data-user-mode="advanced"]').click()
            expect(page.locator("body")).to_have_attribute("data-mode", "simple")
            expect(page.locator("#chatSettingsDialog")).to_be_visible()
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator('[data-user-mode="advanced"]').click()
            expect(page.locator("body")).to_have_attribute("data-mode", "advanced")
            page.locator("#openChatSettings").click()
            for provider, model in [("deepseek", "deepseek-flash"), ("glm", "glm-5.3")]:
                page.locator("#chatProvider").select_option(provider)
                expect(page.locator("#chatModel")).to_have_value(model)
                page.locator("#chatModel").select_option("__custom__")
                page.locator("#chatCustomModel").fill("my-new-model")
                expect(page.locator("#chatCustomModel")).to_have_value("my-new-model")
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator('#chatSettingsDialog [data-user-mode="simple"]').click()
            page.locator('[data-step-target="glossary"]').click()
            page.get_by_role("button", name="Teeth & anatomy", exact=True).click()
            expect(page.locator('#glossaryTerms > div:visible')).to_have_count(8)
            page.locator("#glossarySearch").fill("incisor")
            expect(page.locator('#glossaryTerms > div:visible')).to_have_count(1)
            page.screenshot(path=str(tmp_path / "glossary.png"))
            page.locator('[data-step-target="toothmap"]').click()
            expect(page.locator('#guidedRail')).to_be_visible()
            page.locator('#toothExplorerGrid [data-fdi="11"]').click()
            page.locator('#toothExplorer').screenshot(path=str(tmp_path / "tooth-reference.png"))
            page.evaluate("window.scrollTo(0, 500)")
            assert page.locator('#guidedRail').bounding_box()['y'] == pytest.approx(60, abs=1)
            page.locator('[data-gstep-nav="plan"]').click()
            expect(page.locator('.gstep[data-gstep="plan"]')).to_be_visible()
            page.locator('#teethProfile').click()
            expect(page.locator('.gstep[data-gstep="upload"]')).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator('[data-step-target="toothmap"]').click()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#toothExplorer').screenshot(path=str(tmp_path / "tooth-reference-mobile.png"))
            assert not errors
        finally:
            browser.close()
