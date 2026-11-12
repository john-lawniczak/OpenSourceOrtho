"""Provider credential routing and actionable errors never expose upstream text."""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from orthoplan.evaluation.providers.base import ModelRequest
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider


@pytest.mark.parametrize("status,code,expected", [
    (401, "invalid_api_key", "paste a complete"),
    (403, None, "permissions"), (404, "model_not_found", "model ID"),
    (429, "insufficient_quota", "billing"), (429, None, "Wait briefly"),
])
def test_connection_errors_are_actionable_and_redacted(monkeypatch, status, code, expected):
    seen = {}

    class SDKError(Exception):
        status_code = status

    error = SDKError("secret-key-and-private-plan")
    error.code = code

    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.responses = self

        def create(self, **kwargs):
            raise error

        def close(self):
            seen["closed"] = True

    module = ModuleType("openai")
    module.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://unrelated.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "different-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "different-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "different-project")
    with pytest.raises(RuntimeError) as caught:
        OpenAIProvider(api_key="  supplied-key\n").complete(ModelRequest(system="test", prompt="test"))
    assert expected in str(caught.value)
    assert "secret-key" not in str(caught.value) and "private-plan" not in str(caught.value)
    assert seen["api_key"] == "supplied-key"
    assert seen["base_url"] == "https://api.openai.com/v1"
    assert seen["organization"] == seen["project"] == ""
    assert seen["closed"]


def test_explicit_adapter_endpoint_and_environment_credentials(monkeypatch):
    seen = {}

    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.responses = self

        def create(self, **kwargs):
            return SimpleNamespace(output_text="Educational explanation")

        def close(self):
            pass

    module = ModuleType("openai")
    module.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    OpenAIProvider(base_url="http://explicit.invalid").complete(ModelRequest(system="test", prompt="test"))
    assert seen["base_url"] == "http://explicit.invalid" and seen["api_key"] == "env-key"
    assert "organization" not in seen and "project" not in seen


def test_real_sdk_sends_supplied_bearer_and_omits_empty_scope(monkeypatch):
    """Exercise serialization, not just the SDK constructor arguments."""
    sdk = pytest.importorskip("openai")
    # SDK releases use httpx or httpx2; use the installed client's transport.
    import importlib
    http = importlib.import_module(sdk.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])
    seen = []
    original_client = sdk.OpenAI

    def respond(request):
        seen.append(request)
        return http.Response(200, json={"id": "resp_test", "object": "response", "created_at": 0,
            "status": "completed", "model": "test", "output": [{"type": "message", "id": "msg_test",
            "role": "assistant", "status": "completed", "content": [{"type": "output_text",
            "text": "Educational explanation", "annotations": []}]}]})

    def client(**kwargs):
        return original_client(http_client=sdk.DefaultHttpxClient(transport=http.MockTransport(respond)), **kwargs)

    monkeypatch.setenv("OPENAI_API_KEY", "wrong-environment-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "unrelated-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "unrelated-project")
    monkeypatch.setenv("OPENAI_CUSTOM_HEADERS", "authorization: Bearer wrong-header-key")
    monkeypatch.setattr(sdk, "OpenAI", client)
    result = OpenAIProvider(model="test", api_key="  synthetic-user-key  ").complete(
        ModelRequest(system="test", prompt="test"))
    assert result.text == "Educational explanation"
    assert len(seen) == 1 and str(seen[0].url) == "https://api.openai.com/v1/responses"
    assert seen[0].headers.get_list("authorization") == ["Bearer synthetic-user-key"]
    assert "OpenAI-Organization" not in seen[0].headers
    assert "OpenAI-Project" not in seen[0].headers
