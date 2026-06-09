"""Plan-scoped AI chat gateway.

The chat layer is intentionally advisory and auditable. It packages a bounded
plan context, records which scope was shared, and keeps model output separated
from deterministic findings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from orthoplan.ai_connectors import (
    AIConnector,
    ConnectorKind,
    build_chat_provider,
    connector_catalog,
    connector_for,
)
from orthoplan.api import evaluate_plan
from orthoplan.evaluation.providers.base import ModelProvider, ModelRequest
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.timeline import project_timeline

__all__ = [
    "AIConnector",
    "ConnectorKind",
    "answer_chat_payload",
    "build_chat_context",
    "build_chat_provider",
    "connector_catalog",
    "scope_for",
]

ContextScopeName = Literal["summary", "clinical", "full_plan"]

CHAT_SYSTEM_PROMPT = """You are an educational assistant for OpenSource Ortho.

You may explain the supplied plan context, data gaps, timeline, and deterministic
findings. You must not diagnose, approve treatment, prescribe aligners, claim a
plan is safe, produce or imply a complete treatment plan, authorize printing or
wearing an appliance, or replace review by a licensed dental professional. When
data is missing, say so plainly and ask what record would resolve the uncertainty.
Any physical use is the user's own responsibility and risk.
"""


class AIContextScope(BaseModel):
    name: ContextScopeName = "summary"
    include_plan_snapshot: bool = False
    include_findings: bool = True
    include_data_gaps: bool = True
    include_timeline: bool = True
    include_clinical_controls: bool = True
    include_mesh_metadata: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    session_id: str
    plan_id: str
    plan_hash: str
    connector: AIConnector
    context_scope: AIContextScope
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    plan: dict[str, Any]
    message: str = Field(min_length=1, max_length=2000)
    provider: ConnectorKind = "local"
    model: str | None = None
    context_scope: ContextScopeName = "summary"
    ui_context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    # Browser-supplied credentials/endpoint for live external connectors. These
    # are never persisted, never echoed back in the response, and only sent on an
    # explicit user "Ask AI" action.
    api_key: str | None = Field(default=None, max_length=400)
    endpoint: str | None = Field(default=None, max_length=400)
    # Egress consent gate. External connectors transmit scoped plan context off
    # this machine, so the user must explicitly acknowledge before any call.
    share_acknowledged: bool = False


class ChatResponse(BaseModel):
    ok: bool = True
    session: ChatSession
    context: dict[str, Any]
    caveat: str = (
        "AI chat is educational and advisory only. It cannot diagnose, approve treatment, "
        "produce a complete treatment plan, authorize physical use, or replace review by "
        "a licensed dental professional. Any physical use is the user's own responsibility "
        "and risk."
    )


class ChatErrorResponse(BaseModel):
    ok: bool = False
    errors: list[str]


def scope_for(name: ContextScopeName) -> AIContextScope:
    if name == "full_plan":
        return AIContextScope(
            name=name,
            include_plan_snapshot=True,
            include_mesh_metadata=True,
        )
    if name == "clinical":
        return AIContextScope(name=name, include_mesh_metadata=True)
    return AIContextScope(name=name)


def build_chat_context(plan: TreatmentPlan, scope: AIContextScope) -> dict[str, Any]:
    evaluation = evaluate_plan(plan)
    timeline = project_timeline(plan)
    context: dict[str, Any] = {
        "plan_id": plan.id,
        "title": plan.title,
        "plan_hash": sha256_text(canonical_json(plan.model_dump(mode="json"))),
        "stage_count": len(plan.stages),
        "numbering_system": plan.numbering_system,
        "data_availability": plan.data.model_dump(),
    }
    if scope.include_data_gaps:
        context["data_gaps"] = data_gaps(plan)
    if scope.include_timeline:
        context["timeline"] = timeline.model_dump()
    if scope.include_findings:
        context["findings"] = evaluation["findings"]
    if scope.include_clinical_controls:
        context["clinical_controls"] = evaluation["clinical_controls"]
    if scope.include_mesh_metadata:
        context["mesh_assets"] = [asset.model_dump(mode="json") for asset in plan.mesh_assets]
        context["tooth_meshes"] = [link.model_dump(mode="json") for link in plan.tooth_meshes]
    if scope.include_plan_snapshot:
        context["plan_snapshot"] = plan.model_dump(mode="json")
    return context


def _format_validation_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(request)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def _local_answer(message: str, context: dict[str, Any]) -> str:
    findings = context.get("findings") or []
    gaps = context.get("data_gaps") or []
    timeline = context.get("timeline") or {}
    ui_context = context.get("ui_context") or {}
    stage_count = context.get("stage_count", 0)
    duration = timeline.get("projected_duration_weeks")
    first_gap = gaps[0] if gaps else "no declared gap from the current context"
    first_finding = findings[0]["title"] if findings else "no deterministic finding from the current rules"
    ui_label = ui_context.get("label") or "the current workspace stage"
    ui_purpose = ui_context.get("purpose") or "review the plan context"
    asked = message.strip()
    return (
        f"I can review the current plan context, but only as education. You are in {ui_label}, "
        f"which is used to {ui_purpose}. This plan has {stage_count} "
        f"stage(s)"
        + (f" and projects to about {duration} week(s)" if duration is not None else "")
        + f". The first deterministic signal is: {first_finding}. The first data limitation is: "
        f"{first_gap}. For your question, \"{asked}\", the most useful next step is to compare the "
        "visual movement timeline with the findings and collect any missing records before relying on "
        "the preview for clinical decisions."
    )


def _provider_answer(message: str, context: dict[str, Any], provider: ModelProvider) -> str:
    request = ModelRequest(
        system=CHAT_SYSTEM_PROMPT,
        prompt=(
            "Plan context JSON:\n"
            f"{canonical_json(context)}\n\n"
            f"User question:\n{message}\n\n"
            "Answer conversationally, with the safety boundary from the system message."
        ),
        metadata={"plan_id": str(context.get("plan_id", "")), "context_scope": str(context.get("scope", ""))},
    )
    return provider.complete(request).text


def _resolve_answer(
    request: ChatRequest,
    connector: AIConnector,
    context: dict[str, Any],
    provider: ModelProvider | None,
) -> tuple[str | None, list[str] | None]:
    """Return (answer, None) on success or (None, errors) for the caller to surface.

    A directly injected provider is treated as an explicit gateway. Otherwise an
    external connector kind is built from the request, gated on egress consent.
    """

    used_provider = provider
    if used_provider is None and connector.kind != "local":
        if not request.share_acknowledged:
            return None, [
                f"{connector.label} sends scoped plan context off this machine. Enable "
                "\"Allow an external AI agent to request scoped plan context\" in Connector "
                "Settings to acknowledge before using an external connector."
            ]
        try:
            used_provider = build_chat_provider(
                connector.kind,
                model=request.model,
                api_key=request.api_key,
                endpoint=request.endpoint,
            )
        except ValueError as exc:
            return None, [str(exc)]

    if used_provider is None:
        return _local_answer(request.message, context), None
    try:
        return _provider_answer(request.message, context, used_provider), None
    except Exception as exc:  # noqa: BLE001 - provider failures become user-facing data
        return None, [f"{connector.label} chat failed: {exc}"]


def answer_chat_payload(
    payload: dict[str, Any],
    *,
    provider: ModelProvider | None = None,
) -> dict[str, Any]:
    try:
        request = ChatRequest.model_validate(payload)
        plan = TreatmentPlan.model_validate(request.plan)
    except ValidationError as exc:
        return ChatErrorResponse(errors=_format_validation_errors(exc)).model_dump(mode="json")

    scope = scope_for(request.context_scope)
    context = build_chat_context(plan, scope)
    context["scope"] = scope.name
    context["ui_context"] = request.ui_context
    connector = connector_for(request.provider if provider is None else getattr(provider, "name", "local"))
    if request.model:
        connector.model = request.model

    answer, errors = _resolve_answer(request, connector, context, provider)
    if errors is not None:
        return ChatErrorResponse(errors=errors).model_dump(mode="json")

    plan_hash = str(context["plan_hash"])
    session = ChatSession(
        session_id=request.session_id or f"chat-{plan_hash[:12]}",
        plan_id=plan.id,
        plan_hash=plan_hash,
        connector=connector,
        context_scope=scope,
        messages=[
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=answer),
        ],
    )
    return ChatResponse(session=session, context=context).model_dump(mode="json")
