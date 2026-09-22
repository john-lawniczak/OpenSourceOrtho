"""Plan-generation gateway and orchestration.

This top-level module composes the deterministic generator
(``planning/generate.py``) with deterministic validation, a correctness gate, and
an OPTIONAL, consent-gated model review. It lives at the top level (like
``ai_chat.py``) because it may call a provider - ``planning/`` stays LLM-free.

The pipeline ("the detailed workflow"):

1. Review scan inputs (units, bounds sanity, arch coverage).
2. Generate cap-respecting staging from the best available target.
3. Validate deterministically (``run_rules``).
4. Correctness review: assert staging respects caps and controls. The verdict is
   ``CONSISTENT`` / ``ISSUES`` - never "safe" or "approved".
5. Optional model advisory review - only with an external connector AND egress
   consent; output passes the same ``lint_finding`` gate as every finding.

``generate_plan_payload`` is pure (dict in, dict out) and never raises.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from orthoplan.ai_connectors import ConnectorKind, build_chat_provider, connector_for
from orthoplan.evaluation.advisory import request_advisory
from orthoplan.evaluation.engine import run_rules
from orthoplan.evaluation.local_review import local_notes_advisory
from orthoplan.evaluation.providers.base import ModelProvider
from orthoplan.generation_checks import PipelineStep, correctness_review
from orthoplan.model.assets import bounding_box_sanity
from orthoplan.model.landmarks import ArchLandmarks
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.generate import generate_plan
from orthoplan.planning.timeline import project_timeline

GENERATION_CAVEAT = (
    "Plan generation is deterministic and, when targets are unavailable, educational. "
    "A CONSISTENT verdict means the staging is internally consistent with the configured "
    "caps and controls - NOT that it is safe, approved, clinically appropriate, or "
    "complete. It is not a complete treatment plan, does not diagnose, does not "
    "authorize physical use, and does not replace a licensed dental professional. "
    "Any physical use is the user's own responsibility and risk."
)


class GenerateRequest(BaseModel):
    plan: dict[str, Any]
    # Optional per-tooth crown landmarks ({"landmarks": [...]}) to ground targets
    # in the patient's real positions (preferred over the educational fallback).
    landmarks: dict[str, Any] | None = None
    # Free-text focus/notes appended to the OPTIONAL model review prompt only
    # (e.g. "focus on the lateral incisors"). Never changes deterministic staging.
    notes: str | None = Field(default=None, max_length=2000)
    acknowledge_educational: bool = False
    provider: ConnectorKind = "local"
    model: str | None = None
    api_key: str | None = Field(default=None, max_length=400)
    endpoint: str | None = Field(default=None, max_length=400)
    # Egress consent for the optional model review step (mirrors the chat layer).
    share_acknowledged: bool = False


def _format_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(request)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def _review_scan(plan: TreatmentPlan) -> PipelineStep:
    if not plan.scans:
        return PipelineStep(name="review-scan", status="warning", detail="No scan loaded.")
    notes: list[str] = []
    if not plan.scale_confirmed:
        notes.append("scan units unverified")
    for scan in plan.scans:
        sanity = bounding_box_sanity(scan.asset)
        if sanity:
            notes.append(sanity)
    arches = sorted({scan.arch for scan in plan.scans if scan.arch})
    detail = f"{len(plan.scans)} scan(s); arches: {', '.join(arches) or 'unspecified'}."
    if notes:
        return PipelineStep(name="review-scan", status="warning", detail=f"{detail} {'; '.join(notes)}.")
    return PipelineStep(name="review-scan", detail=detail)


def _external_provider(
    request: GenerateRequest, provider: ModelProvider | None
) -> tuple[ModelProvider | None, str]:
    """Resolve the external model provider, or (None, reason) when only the
    offline local helper is available."""
    if provider is not None:
        return provider, ""
    connector = connector_for(request.provider)
    if connector.kind == "local":
        return None, "local helper selected"
    if not request.share_acknowledged:
        return None, f"{connector.label} review needs the external-agent acknowledgement"
    try:
        return build_chat_provider(
            connector.kind, model=request.model, api_key=request.api_key, endpoint=request.endpoint
        ), ""
    except ValueError as exc:
        return None, str(exc)


def _model_review(
    request: GenerateRequest,
    plan: TreatmentPlan,
    provider: ModelProvider | None,
) -> tuple[list[dict], PipelineStep]:
    used, note = _external_provider(request, provider)
    if used is not None:
        try:
            result = request_advisory(plan, used, notes=request.notes)
        except Exception as exc:  # noqa: BLE001 - provider failures become user-facing data
            return [], PipelineStep(name="model-review", status="warning", detail=f"review failed: {exc}")
        findings = [f.model_dump(mode="json") for f in result.accepted]
        detail = (f"unparseable advisory: {result.parse_error}" if result.parse_error
                  else f"{len(findings)} linted advisory finding(s); {len(result.rejected)} rejected by lint.")
        return findings, PipelineStep(name="model-review", detail=detail)

    # No external model: the offline local helper still acts on the user's notes.
    if request.notes and request.notes.strip():
        local = local_notes_advisory(plan, request.notes)
        suffix = f" ({note})" if note and note != "local helper selected" else ""
        return [f.model_dump(mode="json") for f in local], PipelineStep(
            name="model-review",
            detail=f"local helper (offline) acted on your notes - {len(local)} educational note(s).{suffix}",
        )
    return [], PipelineStep(name="model-review", status="skipped",
                            detail=f"{note}; no notes to review.")


def generate_plan_payload(
    payload: dict[str, Any],
    *,
    provider: ModelProvider | None = None,
) -> dict[str, Any]:
    """Validate a payload, generate + orchestrate a plan, and return data. Never raises."""

    try:
        request = GenerateRequest.model_validate(payload)
        plan = TreatmentPlan.model_validate(request.plan)
        landmarks = ArchLandmarks.model_validate(request.landmarks) if request.landmarks else None
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}

    steps = [_review_scan(plan)]
    generated = generate_plan(
        plan, acknowledge_educational=request.acknowledge_educational, landmarks=landmarks
    )
    steps.append(
        PipelineStep(
            name="generate-targets",
            status="ok" if generated.source != "none" else "warning",
            detail=f"source={generated.source}; {generated.target_tooth_count} target tooth/teeth, "
            f"{generated.aligned_tooth_count} aligned, {len(generated.blocked_teeth)} blocked.",
        )
    )

    findings = run_rules(generated.plan)
    steps.append(
        PipelineStep(name="deterministic-validation", detail=f"{len(findings)} deterministic finding(s).")
    )

    verdict, correctness_step, checks, metrics = correctness_review(
        generated.plan, findings, generated
    )
    steps.append(correctness_step)

    advisory_findings, model_step = _model_review(request, generated.plan, provider)
    steps.append(model_step)

    response = _build_response(generated, steps, checks, verdict, metrics, findings, advisory_findings)
    response["notes"] = request.notes
    return response


def _build_response(generated, steps, checks, verdict, metrics, findings, advisory_findings) -> dict[str, Any]:
    return {
        "ok": True,
        "source": generated.source,
        "requires_acknowledgement": generated.requires_acknowledgement,
        "warnings": generated.warnings,
        "steps": [step.model_dump() for step in steps],
        "checks": [check.model_dump() for check in checks],
        "correctness": {"verdict": verdict, **metrics},
        "stage_count": len(generated.plan.stages),
        "space": {
            "discrepancy_mm": generated.space_discrepancy_mm,
            "residual_mm": generated.space_residual_mm,
            "ipr_count": len(generated.plan.interproximal_reductions),
            "attachment_count": len(generated.plan.attachments),
        },
        "timeline": project_timeline(generated.plan).model_dump(),
        "deterministic_findings": [f.model_dump(mode="json") for f in findings],
        "advisory_findings": advisory_findings,
        "issues": [issue.model_dump() for issue in generated.issues],
        "plan": generated.plan.model_dump(mode="json"),
        "caveat": GENERATION_CAVEAT,
    }
