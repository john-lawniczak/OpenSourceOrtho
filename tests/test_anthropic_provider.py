"""Claude API protocol, credential boundaries, and shared response linting."""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from orthoplan.ai_chat import answer_chat_payload
from orthoplan.ai_connectors import build_chat_provider, connector_for
from orthoplan.evaluation.providers.base import ModelRequest


def stub_sdk(monkeypatch, text="Educational explanation.", stop="end_turn", error=None):
    seen = {}

    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.messages = self

        def create(self, **kwargs):
            seen.update(kwargs)
            if error:
                raise error
            return SimpleNamespace(stop_reason=stop, content=[
                SimpleNamespace(type="thinking", thinking="private reasoning"),
                SimpleNamespace(type="text", text=text),
            ])

        def close(self):
            seen["closed"] = True

    module = ModuleType("anthropic")
    module.Anthropic = Client
    monkeypatch.setitem(sys.modules, "anthropic", module)
    return seen


def test_claude_api_uses_messages_and_explicit_key(monkeypatch):
    seen = stub_sdk(monkeypatch)
    provider = build_chat_provider("anthropic", api_key="test-key", model="custom-model")
    response = provider.complete(ModelRequest(system="boundary", prompt="context"))
    assert seen == {"api_key": "test-key", "timeout": 120, "max_retries": 0, "model": "custom-model",
                    "max_tokens": 4096, "system": "boundary", "messages": [{"role": "user", "content": "context"}],
                    "closed": True}
    assert response.text == "Educational explanation."
    assert response.provider == "anthropic"
    assert connector_for("anthropic").requires_api_key
    assert not connector_for("claude-code").requires_api_key


@pytest.mark.parametrize("text,stop,error", [
    ("", "end_turn", None), ("Partial text", "max_tokens", None),
    ("", "end_turn", ValueError("secret-key private scan")),
])
def test_claude_api_rejects_incomplete_output_and_sanitizes_errors(monkeypatch, text, stop, error):
    seen = stub_sdk(monkeypatch, text=text, stop=stop, error=error)
    with pytest.raises(RuntimeError) as caught:
        build_chat_provider("anthropic", api_key="secret-key").complete(ModelRequest(system="s", prompt="p"))
    assert "secret-key" not in str(caught.value)
    assert "private scan" not in str(caught.value)
    assert seen["closed"]


def test_claude_api_requires_key_and_consent_before_call(monkeypatch):
    seen = stub_sdk(monkeypatch)
    with pytest.raises(ValueError, match="API key"):
        build_chat_provider("anthropic")
    result = answer_chat_payload({"plan": {"id": "test"}, "provider": "anthropic", "message": "Explain", "api_key": "secret"})
    assert result["ok"] is False
    assert not seen


@pytest.mark.parametrize("answer,ok", [("Educational explanation.", True), ("This plan is safe and approved for treatment.", False)])
def test_claude_api_uses_shared_lint_gate(monkeypatch, answer, ok):
    stub_sdk(monkeypatch, text=answer)
    result = answer_chat_payload({"plan": {"id": "test"}, "provider": "anthropic", "message": "Explain",
                                 "api_key": "secret", "share_acknowledged": True})
    assert result["ok"] is ok
    assert "secret" not in str(result)
    if not ok:
        assert answer not in str(result)


def test_missing_sdk_has_install_instruction(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(RuntimeError, match="providers"):
        build_chat_provider("anthropic", api_key="test").complete(ModelRequest(system="s", prompt="p"))
