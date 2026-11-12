"""Assistant settings and conversation regressions against the local server."""
from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from orthoplan.server import Handler  # noqa: E402


@pytest.fixture(scope="module")
def server_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_settings_hide_secrets_and_reset_on_provider_change(server_url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url)
            page.locator("#chatReopenTab").click()
            expect(page.locator("#chatProvider")).not_to_be_visible()
            page.locator("#openChatSettings").click()
            expect(page.get_by_role("dialog")).to_be_visible()
            expect(page.locator("#chatApiKey")).not_to_be_visible()
            page.locator("#chatProvider").select_option("openai")
            page.locator("#chatApiKey").fill("test-key-not-a-secret")
            page.locator("#agentAccessEnabled").check()
            page.get_by_role("button", name="Done", exact=True).click()
            expect(page.locator("#chatApiKey")).not_to_be_visible()
            page.locator("#openChatSettings").click()
            expect(page.locator("#chatApiKey")).to_have_value("test-key-not-a-secret")
            page.locator("#chatProvider").select_option("claude-code")
            expect(page.locator("#chatApiKey")).to_have_value("")
            expect(page.locator("#chatApiKey")).not_to_be_visible()
            expect(page.locator("#agentAccessEnabled")).not_to_be_checked()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).not_to_be_visible()
            expect(page.locator("#openChatSettings")).to_be_focused()
        finally:
            browser.close()


def test_conversation_keeps_prompts_responses_and_mobile_layout(server_url, tmp_path):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(server_url)
            page.locator("#chatReopenTab").click()
            expect(page.locator(".chat-welcome")).to_be_visible()
            page.locator("#chatInput").fill("What records are missing?")
            page.locator("#sendChat").click()
            expect(page.locator(".chat-message.user")).to_have_text("YouWhat records are missing?")
            expect(page.locator("#sendChat")).to_have_text("Send ↑", timeout=15000)
            expect(page.locator(".chat-message.assistant")).to_have_count(1)
            page.locator("#chatInput").fill("Explain the timeline\nand its limits.")
            page.locator("#chatInput").press("Enter")
            expect(page.locator("#sendChat")).to_have_text("Send ↑", timeout=15000)
            expect(page.locator(".chat-message")).to_have_count(4)
            expect(page.locator(".chat-message.user").first).to_contain_text("What records are missing?")
            expect(page.locator(".chat-message.user").last).to_contain_text("Explain the timeline\nand its limits.")
            assert page.locator("#chatMessages").bounding_box()["height"] > 450
            page.screenshot(path=str(tmp_path / "chat-desktop.png"))
            page.locator("#expandChat").click()
            assert page.locator("#aiChatBlock").bounding_box()["width"] > 800
            page.locator("#toggleChatPanel").click()
            expect(page.locator("#aiChatBlock")).not_to_be_visible()
            page.locator("#chatReopenTab").click()
            expect(page.locator(".chat-message")).to_have_count(4)
            page.locator("#themeToggle").click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#chatInput").focus()
            expect(page.locator("#sendChat")).to_be_in_viewport()
            assert page.locator("#aiChatBlock").evaluate("el => el.scrollWidth <= el.clientWidth")
            page.screenshot(path=str(tmp_path / "chat-mobile.png"))
            page.locator("#newChat").click()
            expect(page.locator(".chat-message")).to_have_count(0)
            expect(page.locator(".chat-welcome")).to_be_visible()
            assert not errors
        finally:
            browser.close()


def test_stream_updates_existing_turn_and_preserves_safe_text(server_url):
    import json

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        requests = []
        answer = "Example <img src=x onerror=alert(1)>\nSecond line."

        def stream(route):
            payload = route.request.post_data_json
            requests.append(payload)
            result = {"ok": True, "session": {"session_id": "test-session",
                      "connector": {"label": "Test"}, "context_scope": {"name": "full_plan"},
                      "messages": [{"role": "assistant", "content": answer}]}}
            events = [("delta", {"text": "Example "}), ("delta", {"text": answer[8:]}), ("done", result)]
            body = "".join(f"event: {kind}\ndata: {json.dumps(data)}\n\n" for kind, data in events)
            route.fulfill(status=200, content_type="text/event-stream", body=body)

        try:
            page.route("**/api/chat/stream", stream)
            page.goto(server_url)
            page.locator("#chatReopenTab").click()
            page.locator("#openChatSettings").click()
            page.locator("#chatProvider").select_option("openai")
            page.locator("#chatApiKey").fill("test-key")
            page.locator("#agentAccessEnabled").check()
            page.get_by_role("button", name="Done", exact=True).click()
            for prompt in ("First prompt", "Follow-up"):
                page.locator("#chatInput").fill(prompt)
                page.locator("#sendChat").click()
                expect(page.locator("#sendChat")).to_have_text("Send ↑")
            expect(page.locator(".chat-message")).to_have_count(4)
            expect(page.locator(".chat-message.assistant p").last).to_have_text(answer)
            expect(page.locator("#chatMessages img")).to_have_count(0)
            assert requests[1]["history"] == [
                {"role": "user", "content": "First prompt"},
                {"role": "assistant", "content": answer},
            ]
            page.locator("#newChat").click()
            page.locator("#chatInput").fill("Fresh conversation")
            page.locator("#sendChat").click()
            expect(page.locator("#sendChat")).to_have_text("Send ↑")
            assert requests[-1]["history"] == []
            assert "session_id" not in requests[-1]
        finally:
            browser.close()


def test_authentication_failure_keeps_prompt_and_opens_connection_settings(server_url, tmp_path):
    import json
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        requests = []

        def reject(route):
            requests.append(route.request.post_data_json)
            result = {"ok": False, "errors": ["OpenAI rejected authentication (401). In Settings → OpenAI, paste a complete, active API key."]}
            route.fulfill(status=200, content_type="text/event-stream",
                          body=f"event: done\ndata: {json.dumps(result)}\n\n")

        try:
            page.route("**/api/chat/stream", reject)
            page.goto(server_url)
            page.locator("#openChatSettings").click()
            page.locator("#chatProvider").select_option("openai")
            page.locator("#chatApiKey").fill("  synthetic-key-not-real  ")
            page.locator("#agentAccessEnabled").check()
            page.get_by_role("button", name="Done", exact=True).click()
            page.locator("#chatReopenTab").click()
            page.locator("#chatInput").fill("Explain this sample")
            page.locator("#sendChat").click()
            expect(page.locator(".chat-message.assistant")).to_contain_text("rejected authentication")
            expect(page.locator("#chatInput")).to_have_value("Explain this sample")
            assert requests[0]["api_key"] == "synthetic-key-not-real"
            reuse = page.get_by_role("button", name="Reuse prompt", exact=True).bounding_box()
            settings = page.get_by_role("button", name="Connection settings", exact=True).bounding_box()
            assert settings["x"] >= reuse["x"] + reuse["width"] + 7 or settings["y"] >= reuse["y"] + reuse["height"] + 7
            page.screenshot(path=str(tmp_path / "chat-auth-recovery.png"))
            page.get_by_role("button", name="Connection settings", exact=True).click()
            expect(page.locator("#chatSettingsDialog")).to_be_visible()
            expect(page.locator("#chatApiKey")).to_be_visible()
            assert "synthetic-key-not-real" not in page.evaluate("JSON.stringify(sessionStorage)")
        finally:
            browser.close()
