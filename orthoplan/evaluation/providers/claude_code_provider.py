from __future__ import annotations

import subprocess

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class ClaudeCodeProvider:
    name = "claude-code"

    def __init__(self, model: str = "claude-code-default", command: str = "claude") -> None:
        self.model = model
        self.command = command

    def complete(self, request: ModelRequest) -> ModelResponse:
        prompt = f"{request.system}\n\n{request.prompt}"
        try:
            completed = subprocess.run(
                [self.command, "-p", prompt],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Claude Code CLI command was not found") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise RuntimeError(f"Claude Code provider failed: {detail}") from exc

        return ModelResponse(
            text=completed.stdout.strip(),
            model=self.model,
            provider=self.name,
        )
