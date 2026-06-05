from __future__ import annotations

import subprocess
import sys
from types import ModuleType

import pytest

from orthoplan.evaluation.providers.base import ModelRequest
from orthoplan.evaluation.providers.claude_code_provider import ClaudeCodeProvider
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider


def _request() -> ModelRequest:
    return ModelRequest(system="boundary", prompt="plan")


def test_claude_provider_converts_command_failure_to_runtime_error(monkeypatch) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003 - subprocess test stub
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["claude"],
            stderr="authentication failed",
        )

    monkeypatch.setattr(subprocess, "run", fail_run)

    with pytest.raises(RuntimeError, match="authentication failed"):
        ClaudeCodeProvider().complete(_request())


def test_openai_provider_converts_sdk_failure_to_runtime_error(monkeypatch) -> None:
    class FakeResponses:
        def create(self, **kwargs):  # noqa: ANN003 - SDK-shaped test stub
            raise ValueError("rate limit")

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003 - SDK-shaped test stub
            self.responses = FakeResponses()

    fake_module = ModuleType("openai")
    fake_module.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match="OpenAIProvider request failed: rate limit"):
        OpenAIProvider().complete(_request())
