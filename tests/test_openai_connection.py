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
