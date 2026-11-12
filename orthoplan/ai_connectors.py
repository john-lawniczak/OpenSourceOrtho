"""Connector catalog and live provider construction for the AI chat layer.

Kept separate from chat orchestration so connector configuration and credential
handling have a single, small ownership boundary. Credentials and endpoints are
supplied per request and are never stored here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from orthoplan.evaluation.providers.anthropic_provider import AnthropicProvider
from orthoplan.evaluation.providers.base import ModelProvider
from orthoplan.evaluation.providers.compatible_provider import CompatibleProvider
from orthoplan.evaluation.providers.claude_code_provider import ClaudeCodeProvider
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider

ConnectorKind = Literal["local", "openai", "anthropic", "claude-code", "mcp", "open-source", "deepseek", "glm"]


class AIConnector(BaseModel):
    """Configuration metadata for a model/MCP connector."""

    id: str
    kind: ConnectorKind = "local"
    label: str
    model: str | None = None
    endpoint: str | None = None
    enabled: bool = False
    shares_patient_data: bool = False
    requires_api_key: bool = False
    supports_streaming: bool = False
    models: list[str] = Field(default_factory=list)
    allow_custom_model: bool = False
    notes: str | None = None


def connector_catalog() -> list[AIConnector]:
    return [
        AIConnector(
            id="local", kind="local",
            label="Local educational helper",
            model="local-educational-helper",
            enabled=True,
            models=["local-educational-helper"],
            notes="No key required; plan context stays on this machine.",
        ),
        AIConnector(
            id="openai", kind="openai",
            label="OpenAI",
            model="gpt-6.1-sol",
            shares_patient_data=True,
            requires_api_key=True,
            supports_streaming=True,
            models=["gpt-6.1-sol", "gpt-6-astra", "gpt-6.1-terra", "gpt-6-luna", "gpt-5.5"],
            allow_custom_model=True,
            notes="Live connector; supply an API key in Connector Settings to enable.",
        ),
        *_claude_connectors(),
        AIConnector(id="deepseek", kind="deepseek", label="DeepSeek", model="deepseek-flash",
                    endpoint="https://api.deepseek.com", shares_patient_data=True,
                    requires_api_key=True, models=["deepseek-flash", "deepseek-v4-pro"],
                    allow_custom_model=True),
        AIConnector(id="glm", kind="glm", label="Z.ai · GLM", model="glm-5.3",
                    endpoint="https://api.z.ai/api/paas/v4/", shares_patient_data=True,
                    requires_api_key=True, models=["glm-5.3"], allow_custom_model=True),
        AIConnector(
            id="mcp", kind="mcp",
            label="OpenAI-compatible host",
            model="mcp-model",
            endpoint="user supplied",
            shares_patient_data=True,
            requires_api_key=True,
            supports_streaming=True,
            models=["mcp-model"],
            allow_custom_model=True,
        ),
        AIConnector(
            id="open-source", kind="open-source",
            label="Local / open-weight model",
            model="local-model",
            endpoint="local or user supplied",
            shares_patient_data=True,
            models=["local-model"],
            allow_custom_model=True,
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
        return OpenAIProvider(model=model or "gpt-6.1-sol", api_key=api_key)
    if kind == "anthropic":
        if not api_key:
            raise ValueError("Add an Anthropic API key in Settings to use Claude API.")
        return AnthropicProvider(model=model or connector_for(kind).model, api_key=api_key)
    if kind == "claude-code":
        return ClaudeCodeProvider(model=model or "claude-code-default")
    if kind in {"deepseek", "glm"}:
        connector = connector_for(kind)
        if not api_key:
            raise ValueError(f"Add an API key in Settings to use {connector.label}.")
        return CompatibleProvider(model=model or connector.model, api_key=api_key,
                                  base_url=connector.endpoint, name=kind)
    if kind in {"mcp", "open-source"}:
        if not endpoint:
            raise ValueError(f"Add a model endpoint URL in Connector Settings to use the {kind} connector.")
        # These hosts expose OpenAI-compatible APIs; reuse the adapter with a base
        # URL. A key is optional for local/open hosts that do not require one.
        return CompatibleProvider(model=model or "local-model", api_key=api_key or "not-required", base_url=endpoint, name=kind)
    raise ValueError(f"Unsupported chat connector: {kind}")


def _claude_connectors() -> list[AIConnector]:
    """Distinguish API-key authentication from local CLI sign-in."""
    return [
        AIConnector(
            id="anthropic", kind="anthropic", label="Claude API (Anthropic)",
            model="claude-sonnet-5-5", shares_patient_data=True,
            requires_api_key=True,
            models=["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
            allow_custom_model=True,
            notes="Use an Anthropic API key; separate from Claude Code CLI sign-in.",
        ),
        AIConnector(
            id="claude-code", kind="claude-code",
            label="Claude Code (local CLI)",
            model="claude-code-default",
            shares_patient_data=True,
            requires_api_key=False,
            models=["claude-code-default", "opus", "sonnet", "haiku"],
            allow_custom_model=True,
            notes="Live CLI connector; requires the local Claude Code CLI on PATH.",
        ),
    ]
