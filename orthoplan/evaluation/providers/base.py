from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class ModelRequest(BaseModel):
    system: str
    prompt: str
    metadata: dict[str, str] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    text: str
    model: str
    provider: str


class ModelProvider(Protocol):
    name: str

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return advisory text. Callers must lint parsed findings separately."""

