"""Text adapter for hosted and local OpenAI Chat Completions-compatible APIs."""
from __future__ import annotations

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class CompatibleProvider:
    def __init__(self, *, model: str, api_key: str, base_url: str, name: str) -> None:
        self.model, self.name = model, name
        self._api_key, self._base_url = api_key, base_url

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install provider dependencies with: pip install -e '.[providers]'") from exc
        try:
            with OpenAI(api_key=self._api_key, base_url=self._base_url, timeout=120, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": request.system},
                              {"role": "user", "content": request.prompt}],
                )
            text = response.choices[0].message.content
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Provider returned no text response")
        except Exception as exc:
            # SDK exception strings can contain request headers or upstream bodies.
            raise RuntimeError(f"{self.name} request failed ({type(exc).__name__}); check model, endpoint and key.") from exc
        return ModelResponse(text=text, model=self.model, provider=self.name)
