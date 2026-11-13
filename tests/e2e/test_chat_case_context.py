"""Explicit case context and a compact composer without lost drafts."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_user_one_context_survives_return_and_reload(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            page.locator("#reviewWorkspaceLink").click()
            page.locator("#topbarAskAI").click()
            expect(page.locator("#chatCaseSource")).to_have_value("user_one")
            expect(page.locator("#chatContextHint")).to_contain_text("USER_ONE")
            page.locator("#chatInput").fill("What records are available?")
            with page.expect_request("**/api/chat") as request:
                page.locator("#sendChat").click()
            assert request.value.post_data_json["case_source"] == "user_one"
            expect(page.locator(".chat-message.assistant")).to_contain_text("scan records", timeout=10000)
            expect(page.locator("#chatComposer")).to_have_attribute("data-expanded", "false")
            page.reload()
            expect(page.locator("#chatCaseSource")).to_have_value("user_one")
            page.locator("#chatCaseSource").select_option("workspace")
            page.locator("#chatInput").fill("Now explain the current workspace")
            with page.expect_request("**/api/chat") as request:
                page.locator("#sendChat").click()
            assert request.value.post_data_json["case_source"] == "workspace"
            page.reload()
            expect(page.locator("#chatCaseSource")).to_have_value("workspace")
            page.screenshot(path=str(tmp_path / "case-context-chat.png"))
        finally:
            browser.close()


def test_composer_expands_on_focus_and_keeps_collapsed_draft(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        try:
            page.goto(server_url)
            page.locator("#topbarAskAI").click()
            composer = page.locator("#chatComposer")
            expect(page.locator("#chatInput")).to_be_focused()
            page.locator("#collapseChatComposer").click()
            compact = composer.bounding_box()["height"]
            assert compact < 85
            page.locator("#chatInput").fill("Keep this unfinished question")
            assert composer.bounding_box()["height"] > compact + 75
            page.locator("#collapseChatComposer").click()
            expect(composer).to_have_attribute("data-expanded", "false")
            expect(page.locator("#chatInput")).to_have_value("Keep this unfinished question")
            page.locator("#chatInput").focus()
            expect(composer).to_have_attribute("data-expanded", "true")
            page.locator("#chatCaseSource").focus()
            expect(composer).to_have_attribute("data-expanded", "false")
            page.reload()
            expect(page.locator("#chatInput")).to_have_value("Keep this unfinished question")
            assert composer.bounding_box()["height"] < 85
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(tmp_path / "compact-composer-mobile.png"))
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        finally:
            browser.close()
