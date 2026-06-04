from __future__ import annotations

import os

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-5.5") -> None:
        self.model = model

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install provider dependencies with: pip install -e '.[providers]'") from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIProvider")

        client = OpenAI()
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.prompt},
                ],
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAIProvider request failed: {exc}") from exc
        return ModelResponse(text=response.output_text, model=self.model, provider=self.name)
