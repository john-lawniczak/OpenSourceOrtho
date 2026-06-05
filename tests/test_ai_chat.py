from __future__ import annotations

from orthoplan.ai_chat import answer_chat_payload, build_chat_context, connector_catalog, scope_for
from orthoplan.model.plan import Stage, ToothDelta, ToothId, TreatmentPlan


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
        }
    )

    assert result["ok"] is True
    assert result["session"]["connector"]["kind"] == "local"
    assert result["session"]["connector"]["model"] == "local-test-model"
    assert result["session"]["context_scope"]["name"] == "summary"
    assert result["session"]["messages"][0]["role"] == "user"
    assert result["session"]["messages"][1]["role"] == "assistant"
    assert result["context"]["plan_hash"] == result["session"]["plan_hash"]


def test_external_chat_connector_requires_explicit_gateway() -> None:
    result = answer_chat_payload(
        {
            "plan": _plan().model_dump(mode="json"),
            "message": "Ask an external model",
            "provider": "openai",
            "context_scope": "summary",
        }
    )

    assert result["ok"] is False
    assert "not enabled" in result["errors"][0]
