"""Connector catalog and live provider construction for the AI chat layer.

Kept separate from chat orchestration so connector configuration and credential
handling have a single, small ownership boundary. Credentials and endpoints are
supplied per request and are never stored here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from orthoplan.evaluation.providers.base import ModelProvider
from orthoplan.evaluation.providers.claude_code_provider import ClaudeCodeProvider
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider

ConnectorKind = Literal["local", "openai", "claude-code", "mcp", "odysseus", "open-source"]


class AIConnector(BaseModel):
    """Configuration metadata for a model/MCP connector."""

    id: str
    kind: ConnectorKind = "local"
    label: str
    model: str | None = None
    endpoint: str | None = None
    enabled: bool = False
    shares_patient_data: bool = False
    notes: str | None = None


def connector_catalog() -> list[AIConnector]:
    return [
        AIConnector(id="local", kind="local", label="Local educational helper", enabled=True),
        AIConnector(
            id="openai",
            kind="openai",
            label="OpenAI",
            model="configured externally",
            shares_patient_data=True,
            notes="Live connector; supply an API key in Connector Settings to enable.",
        ),
        AIConnector(
            id="claude-code",
            kind="claude-code",
            label="Claude Code",
            model="configured externally",
            shares_patient_data=True,
            notes="Live CLI connector; requires the local Claude Code CLI on PATH.",
        ),
        AIConnector(
            id="mcp",
            kind="mcp",
            label="MCP-compatible model host",
            endpoint="user supplied",
            shares_patient_data=True,
        ),
        AIConnector(
            id="odysseus",
            kind="odysseus",
            label="Odysseus",
            endpoint="user supplied",
            shares_patient_data=True,
        ),
        AIConnector(
            id="open-source",
            kind="open-source",
            label="Open-source local model",
            endpoint="local or user supplied",
            shares_patient_data=True,
        ),
    ]


def connector_for(kind: str) -> AIConnector:
    for connector in connector_catalog():
        if connector.kind == kind:
            return connector
    return connector_catalog()[0]


def build_chat_provider(
    kind: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    endpoint: str | None = None,
) -> ModelProvider:
    """Construct a live model provider for an external connector kind.

    Credentials and endpoints are supplied per request (never stored). Raises a
    ``ValueError`` with a user-facing message when required configuration for the
    selected connector is missing.
    """

    if kind == "openai":
        if not api_key:
            raise ValueError("Add an API key in Connector Settings to use the OpenAI connector.")
        return OpenAIProvider(model=model or "gpt-5.5", api_key=api_key)
    if kind == "claude-code":
        return ClaudeCodeProvider(model=model or "claude-code-default")
    if kind in {"mcp", "odysseus", "open-source"}:
        if not endpoint:
            raise ValueError(f"Add a model endpoint URL in Connector Settings to use the {kind} connector.")
        # These hosts expose OpenAI-compatible APIs; reuse the adapter with a base
        # URL. A key is optional for local/open hosts that do not require one.
        return OpenAIProvider(model=model or "local-model", api_key=api_key or "not-required", base_url=endpoint)
    raise ValueError(f"Unsupported chat connector: {kind}")
