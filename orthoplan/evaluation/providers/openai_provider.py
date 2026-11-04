from __future__ import annotations

import os

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        model: str = "gpt-6.1-sol",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        # An explicitly supplied key takes precedence; otherwise fall back to the
        # process environment. ``base_url`` lets this same adapter drive any
        # OpenAI-compatible host (MCP / open-source or self-hosted local model server).
        self._api_key = api_key
        self._base_url = base_url

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install provider dependencies with: pip install -e '.[providers]'") from exc

        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIProvider")

        client = OpenAI(api_key=api_key, base_url=self._base_url, timeout=120, max_retries=0)
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.prompt},
                ],
            )
            text = response.output_text
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Provider returned no text response")
        except Exception as exc:
            raise RuntimeError(f"OpenAIProvider request failed ({type(exc).__name__}); check model and credentials.") from exc
        finally:
            client.close()
        return ModelResponse(text=text, model=self.model, provider=self.name)
