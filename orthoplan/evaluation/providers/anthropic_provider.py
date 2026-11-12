"""Claude Messages API adapter; credentials are supplied for this request only."""
from __future__ import annotations

from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-5-5", *, api_key: str) -> None:
        self.model = model
        self._api_key = api_key

    def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("Install provider dependencies with: pip install -e '.[providers]'") from exc

        client = None
        try:
            client = Anthropic(api_key=self._api_key, timeout=120, max_retries=0)
            response = client.messages.create(
                model=self.model, max_tokens=4096, system=request.system,
                messages=[{"role": "user", "content": request.prompt}],
            )
            if response.stop_reason != "end_turn":
                raise ValueError("Provider did not finish its answer")
            text = "\n".join(block.text for block in response.content if block.type == "text")
            if not text.strip():
                raise ValueError("Provider returned no text response")
        except Exception as exc:
            raise RuntimeError(
                f"Claude API request failed ({type(exc).__name__}); check model, credentials and API credits."
            ) from exc
        finally:
            if client is not None:
                client.close()
        return ModelResponse(text=text, model=self.model, provider=self.name)
