from __future__ import annotations

import json

import pytest

from orthoplan.ai_chat import (
    answer_chat_payload,
    build_chat_context,
    build_chat_provider,
    connector_catalog,
    scope_for,
)
from orthoplan.evaluation.providers.base import ModelRequest, ModelResponse
from orthoplan.evaluation.providers.openai_provider import OpenAIProvider
from orthoplan.model.plan import Stage, ToothDelta, ToothId, TreatmentPlan


class _FakeProvider:
    name = "openai"

    def __init__(self) -> None:
        self.seen: ModelRequest | None = None

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.seen = request
        return ModelResponse(text="Educational external answer.", model="fake", provider=self.name)


def _plan() -> TreatmentPlan:
    return TreatmentPlan(
        id="chat-plan",
        title="Chat plan",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )


def test_connector_catalog_models_external_connectors_as_disabled_by_default() -> None:
    connectors = {connector.kind: connector for connector in connector_catalog()}

    assert connectors["local"].enabled is True
    assert connectors["openai"].enabled is False
    assert connectors["openai"].shares_patient_data is True
    assert connectors["mcp"].endpoint == "user supplied"


def test_summary_context_excludes_full_plan_snapshot() -> None:
    context = build_chat_context(_plan(), scope_for("summary"))

    assert context["plan_id"] == "chat-plan"
    assert "findings" in context
    assert "plan_snapshot" not in context
    assert "mesh_assets" not in context


def test_full_plan_context_includes_immutable_snapshot_payload() -> None:
    context = build_chat_context(_plan(), scope_for("full_plan"))

    assert context["plan_snapshot"]["id"] == "chat-plan"
    assert "plan_hash" in context


def test_local_chat_returns_auditable_session() -> None:
    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "What are the limitations?",
            "provider": "local",
            "model": "local-test-model",
            "context_scope": "summary",
            "ui_context": {
                "label": "Guided step 4: Review",
                "purpose": "summarize the tray count and projected duration",
            },
        }
    )

    assert result["ok"] is True
    assert result["session"]["connector"]["kind"] == "local"
    assert result["session"]["connector"]["model"] == "local-test-model"
    assert result["session"]["context_scope"]["name"] == "summary"
    assert result["session"]["messages"][0]["role"] == "user"
    assert result["session"]["messages"][1]["role"] == "assistant"
    assert "Guided step 4: Review" in result["session"]["messages"][1]["content"]
    assert result["context"]["ui_context"]["label"] == "Guided step 4: Review"
    assert result["context"]["plan_hash"] == result["session"]["plan_hash"]


def test_external_connector_requires_share_acknowledgement() -> None:
    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Ask an external model",
            "provider": "openai",
            "context_scope": "summary",
            "api_key": "sk-secret-test-key",
        }
    )

    assert result["ok"] is False
    assert "off this machine" in result["errors"][0]


def test_external_connector_requires_api_key_after_consent() -> None:
    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Ask an external model",
            "provider": "openai",
            "context_scope": "summary",
            "share_acknowledged": True,
        }
    )

    assert result["ok"] is False
    assert "API key" in result["errors"][0]


def test_external_connector_calls_live_provider_and_hides_key(monkeypatch) -> None:
    fake = _FakeProvider()
    monkeypatch.setattr("orthoplan.ai_chat.build_chat_provider", lambda *a, **k: fake)

    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Explain the timeline",
            "provider": "openai",
            "model": "gpt-test",
            "context_scope": "summary",
            "api_key": "sk-secret-test-key",
            "share_acknowledged": True,
        }
    )

    assert result["ok"] is True
    assert result["session"]["connector"]["kind"] == "openai"
    assert result["session"]["messages"][1]["content"] == "Educational external answer."
    # The boundary system prompt reaches the provider.
    assert "licensed dental professional" in fake.seen.system
    # The API key must never appear anywhere in the serialized response.
    assert "sk-secret-test-key" not in json.dumps(result)


def test_external_connector_surfaces_provider_failure_as_data(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("rate limit")

    fake = _FakeProvider()
    monkeypatch.setattr(fake, "complete", boom)
    monkeypatch.setattr("orthoplan.ai_chat.build_chat_provider", lambda *a, **k: fake)

    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Explain the timeline",
            "provider": "openai",
            "context_scope": "summary",
            "api_key": "sk-secret-test-key",
            "share_acknowledged": True,
        }
    )

    assert result["ok"] is False
    assert "rate limit" in result["errors"][0]


def test_injected_provider_is_treated_as_explicit_gateway() -> None:
    fake = _FakeProvider()
    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Explain the timeline",
            "provider": "openai",
            "context_scope": "summary",
        },
        provider=fake,
    )

    assert result["ok"] is True
    assert result["session"]["messages"][1]["content"] == "Educational external answer."


def test_build_chat_provider_maps_connector_kinds() -> None:
    assert isinstance(build_chat_provider("openai", api_key="k"), OpenAIProvider)
    endpoint_provider = build_chat_provider("open-source", endpoint="http://127.0.0.1:1234/v1")
    assert isinstance(endpoint_provider, OpenAIProvider)

    with pytest.raises(ValueError, match="API key"):
        build_chat_provider("openai")
    with pytest.raises(ValueError, match="endpoint"):
        build_chat_provider("mcp")
    with pytest.raises(ValueError, match="Unsupported"):
        build_chat_provider("nope")
