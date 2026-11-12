from __future__ import annotations

import subprocess

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class ClaudeCodeProvider:
    name = "claude-code"

    def __init__(self, model: str = "claude-code-default", command: str = "claude") -> None:
        self.model = model
        self.command = command

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            completed = subprocess.run(
                [self.command, "-p", "--bare", "--tools", "", "--disallowedTools", "*",
                 "--no-session-persistence", "--system-prompt", request.system,
                 *([] if self.model == "claude-code-default" else ["--model", self.model])],
                input=request.prompt, timeout=120,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Claude Code CLI command was not found") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Claude Code provider failed; check CLI version, authentication and model.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Claude Code request timed out after 120 seconds.") from exc

        return ModelResponse(
            text=completed.stdout.strip(),
            model=self.model,
            provider=self.name,
        )
