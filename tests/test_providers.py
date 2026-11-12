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

    with pytest.raises(RuntimeError, match="check CLI version"):
        ClaudeCodeProvider().complete(_request())


def test_openai_provider_converts_sdk_failure_to_runtime_error(monkeypatch) -> None:
    class FakeResponses:
        def create(self, **kwargs):  # noqa: ANN003 - SDK-shaped test stub
            raise ValueError("rate limit")

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003 - SDK-shaped test stub
            self.responses = FakeResponses()

        def close(self):
            pass

    fake_module = ModuleType("openai")
    fake_module.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match="OpenAIProvider request failed"):
        OpenAIProvider().complete(_request())


def test_claude_is_text_only_ephemeral_and_receives_context_on_stdin(monkeypatch):
    seen = {}

    def run(command, **kwargs):
        seen.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="Explanation")

    monkeypatch.setattr(subprocess, "run", run)
    ClaudeCodeProvider().complete(ModelRequest(system="boundary", prompt="private scan context"))
    assert "private scan context" not in seen["command"]
    assert seen["input"] == "private scan context"
    assert seen["timeout"] == 120
    command = seen["command"]
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--disallowedTools") + 1] == "*"
    assert "--bare" in command and "--no-session-persistence" in command


def test_claude_timeout_and_stderr_do_not_leak_context(monkeypatch):
    for error in [subprocess.TimeoutExpired("claude", 120, output="private scan"),
                  subprocess.CalledProcessError(1, "claude", stderr="secret-key private scan")]:
        def fail(*args, **kwargs):
            raise error
        monkeypatch.setattr(subprocess, "run", fail)
        with pytest.raises(RuntimeError) as caught:
            ClaudeCodeProvider().complete(_request())
        assert "private scan" not in str(caught.value)
        assert "secret-key" not in str(caught.value)
