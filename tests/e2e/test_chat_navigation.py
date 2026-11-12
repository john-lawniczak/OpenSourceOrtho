"""Chat survives page boundaries without retaining connection secrets."""
import json

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from tests.e2e.test_chat_workspace import server_url as _server_url  # noqa: E402


server_url = _server_url


@pytest.fixture
def chat_page(server_url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(server_url, wait_until="load")
        page.locator("#chatReopenTab").click()
        yield page
        browser.close()


def configure(page, provider="anthropic", key="test-key"):
    page.locator("#openChatSettings").click()
    page.locator("#chatProvider").select_option(provider)
    page.locator("#chatApiKey").fill(key)
    page.locator("#agentAccessEnabled").check()
    page.get_by_role("button", name="Done", exact=True).click()


def test_navigation_reload_and_new_chat_preserve_draft_and_history(chat_page, server_url):
    page = chat_page
    page.locator("#chatInput").fill("Explain the missing records")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#sendChat")).to_have_text("Send ↑")
    expect(page.locator(".chat-message")).to_have_count(2)
    page.locator("#chatInput").fill("Unsent question\nabout this scan")
    page.locator("#toggleChatPanel").click()
    page.locator('[data-step-target="glossary"]').click()
    page.locator("#chatReopenTab").click()
    expect(page.locator("#chatInput")).to_have_value("Unsent question\nabout this scan")
    expect(page.locator(".chat-message")).to_have_count(2)
    page.locator("#expandChat").click()
    page.goto(server_url + "/region-review.html", wait_until="load")
    page.go_back(wait_until="load")
    expect(page.locator("#chatInput")).to_have_value("Unsent question\nabout this scan")
    expect(page.locator(".chat-message")).to_have_count(2)
    expect(page.locator("#expandChat")).to_have_text("Dock")
    page.reload(wait_until="load")
    expect(page.locator("#chatInput")).to_have_value("Unsent question\nabout this scan")
    expect(page.locator(".chat-message")).to_have_count(2)
    page.locator("#newChat").click()
    page.reload(wait_until="load")
    expect(page.locator(".chat-message")).to_have_count(0)
    expect(page.locator("#chatInput")).to_have_value("")


def test_claude_key_and_consent_are_never_persisted(chat_page, tmp_path):
    page = chat_page
    configure(page, key="test-secret-not-real")
    page.locator("#chatInput").fill("Saved draft")
    snapshot = page.evaluate("JSON.stringify({ ...sessionStorage, ...localStorage })")
    assert "test-secret-not-real" not in snapshot
    stored = page.evaluate("JSON.parse(sessionStorage.getItem('orthoplan-chat-session-v1'))")
    assert "agentAccessEnabled" not in stored and "apiKey" not in stored and "agentEndpoint" not in stored
    page.reload(wait_until="load")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#chatSettingsDialog")).to_be_visible()
    expect(page.locator("#chatProvider")).to_have_value("anthropic")
    expect(page.locator("#chatApiKey")).to_be_visible()
    expect(page.locator("#chatApiKey")).to_have_value("")
    expect(page.locator("#chatApiKey")).to_be_focused()
    expect(page.locator("#agentAccessEnabled")).not_to_be_checked()
    expect(page.locator("#chatInput")).to_have_value("Saved draft")
    page.screenshot(path=str(tmp_path / "claude-api-settings.png"))


def test_failure_keeps_prompt_and_retry_excludes_failed_turn(chat_page):
    page = chat_page
    requests = []

    def respond(route):
        requests.append(route.request.post_data_json)
        result = {"ok": False, "errors": ["Temporary test failure"]} if len(requests) == 1 else {
            "ok": True, "session": {"session_id": "test-session", "messages": [{"role": "assistant", "content": "Explanation."}]}}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(result))

    page.route("**/api/chat", respond)
    configure(page)
    page.locator("#chatInput").fill("My original question")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#chatInput")).to_have_value("My original question")
    expect(page.get_by_role("button", name="Reuse prompt")).to_be_visible()
    page.reload(wait_until="load")
    configure(page)
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#chatStatus")).to_have_text("Ready")
    assert requests[-1]["history"] == []
    assert requests[-1]["provider"] == "anthropic"
    assert requests[-1]["api_key"] == "test-key"
    assert requests[-1]["message"] == "My original question"


def test_pending_navigation_recovers_prompt_without_auto_resend(chat_page, server_url):
    page = chat_page
    page.route("**/api/chat", lambda route: None)
    page.locator("#chatInput").fill("Interrupted question")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#sendChat")).to_have_text("Thinking…")
    page.goto(server_url + "/region-review.html", wait_until="domcontentloaded")
    page.goto(server_url, wait_until="load")
    expect(page.locator("#chatInput")).to_have_value("Interrupted question")
    expect(page.locator("#sendChat")).to_have_text("Send ↑")
    expect(page.locator(".chat-message.assistant")).to_contain_text("interrupted by navigation")
    expect(page.locator("#sendChat")).to_be_enabled()


def test_storage_failure_is_visible_without_breaking_chat(chat_page):
    page = chat_page
    page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('quota'); }; }")
    page.locator("#chatInput").fill("Keep this draft")
    expect(page.locator("#chatPersistenceNotice")).to_contain_text("storage is unavailable or full")
    expect(page.locator("#sendChat")).to_be_enabled()


def test_followup_after_reload_sends_preserved_successful_history(chat_page):
    page = chat_page
    requests = []

    def respond(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json", body=json.dumps({
            "ok": True, "session": {"session_id": "kept-session", "messages": [
                {"role": "assistant", "content": "First explanation."}]}}))

    page.route("**/api/chat", respond)
    page.locator("#chatInput").fill("First question")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#chatStatus")).to_have_text("Ready")
    page.reload(wait_until="load")
    page.locator("#chatInput").fill("Follow-up")
    page.locator("#chatInput").focus()
    page.locator("#sendChat").click()
    expect(page.locator("#chatStatus")).to_have_text("Ready")
    assert requests[-1]["session_id"] == "kept-session"
    assert requests[-1]["history"] == [{"role": "user", "content": "First question"},
                                        {"role": "assistant", "content": "First explanation."}]
