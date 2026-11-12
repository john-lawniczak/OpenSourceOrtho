"""Offline fault tests always run; live tests require an explicit environment opt-in."""

import os
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from orthoplan.evaluation.providers.base import ModelRequest
from orthoplan.evaluation.providers.compatible_provider import CompatibleProvider
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider


@pytest.mark.parametrize("adapter", ["compatible", "openai"])
@pytest.mark.parametrize("failure", ["authentication", "timeout", "malformed", "empty"])
def test_provider_failures_are_bounded_and_redacted(monkeypatch, adapter, failure):
    seen = {}

    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.chat = SimpleNamespace(completions=self)
            self.responses = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def close(self):
            seen["closed"] = True

        def create(self, **kwargs):
            if failure == "authentication":
                raise PermissionError("secret-token upstream-body")
            if failure == "timeout":
                raise TimeoutError("secret-token upstream-body")
            if failure == "malformed":
                return SimpleNamespace()
            return SimpleNamespace(
                output_text="", choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
            )

    module = ModuleType("openai")
    module.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", module)
    provider = (
        CompatibleProvider(
            model="test", api_key="secret-token", base_url="http://unused", name="test"
        )
        if adapter == "compatible"
        else OpenAIProvider(model="test", api_key="secret-token")
    )
    with pytest.raises(RuntimeError) as caught:
        provider.complete(ModelRequest(system="synthetic", prompt="test"))
    assert "secret-token" not in str(caught.value)
    assert seen["timeout"] == 120 and seen["max_retries"] == 0 and seen["closed"]


@pytest.mark.parametrize("provider", ["openai", "deepseek", "glm", "open-source", "claude-code"])
def test_live_provider(provider):
    enabled = os.environ.get("ORTHOPLAN_LIVE_PROVIDERS", "").split(",")
    if provider not in enabled:
        pytest.skip("opt in with ORTHOPLAN_LIVE_PROVIDERS; may incur provider charges")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "orthoplan.validation.provider_smoke",
            "--live",
            "--provider",
            provider,
        ],
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert result.returncode == 0, f"{provider} connectivity test failed (details suppressed)"
