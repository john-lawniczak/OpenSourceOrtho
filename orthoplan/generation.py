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

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from orthoplan.ai_connectors import ConnectorKind, build_chat_provider, connector_for
from orthoplan.evaluation.advisory import request_advisory
from orthoplan.evaluation.engine import run_rules
from orthoplan.evaluation.providers.base import ModelProvider
from orthoplan.model.assets import bounding_box_sanity
from orthoplan.model.landmarks import ArchLandmarks
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.generate import generate_plan
from orthoplan.planning.timeline import project_timeline

CorrectnessVerdict = Literal["CONSISTENT", "ISSUES", "NOT_APPLICABLE"]

GENERATION_CAVEAT = (
    "Plan generation is deterministic and, when targets are unavailable, educational. "
    "A CONSISTENT verdict means the staging is internally consistent with the configured "
    "caps and controls - NOT that it is safe, approved, clinically appropriate, or "
    "complete. It does not diagnose or replace a licensed dental professional."
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


class PipelineStep(BaseModel):
    name: str
    status: Literal["ok", "warning", "skipped"] = "ok"
    detail: str = ""


class Check(BaseModel):
    """One named correctness check. ``gate`` checks fail the verdict; ``warning``
    and ``info`` checks are surfaced but do not flip CONSISTENT to ISSUES."""

    name: str
    passed: bool
    severity: Literal["gate", "warning", "info"] = "gate"
    detail: str = ""


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


_AXES = (
    "translate_x_mm", "translate_y_mm", "translate_z_mm",
    "rotate_tip_deg", "rotate_torque_deg", "rotate_rotation_deg",
)


def _cumulative(plan: TreatmentPlan) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for stage in plan.stages:
        for delta in stage.deltas:
            bucket = totals.setdefault(delta.tooth.value, {a: 0.0 for a in _AXES})
            for axis in _AXES:
                bucket[axis] += getattr(delta, axis)
    return totals


def _targets_reached_check(plan: TreatmentPlan, generated) -> Check:
    """Every non-blocked target tooth's cumulative movement must equal its target."""
    blocked = set(generated.blocked_teeth)
    want = _cumulative_from_deltas(generated.requested_targets)
    got = _cumulative(plan)
    mismatches: list[str] = []
    for tooth, target in want.items():
        if tooth in blocked:
            continue
        actual = got.get(tooth, {a: 0.0 for a in _AXES})
        if any(abs(target[a] - actual[a]) > 1e-6 for a in _AXES):
            mismatches.append(tooth)
    passed = not mismatches
    detail = ("cumulative movement reaches every requested target"
              if passed else f"targets not reached for: {', '.join(sorted(mismatches))}")
    return Check(name="targets-reached", passed=passed, detail=detail)


def _cumulative_from_deltas(deltas) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for delta in deltas:
        bucket = totals.setdefault(delta.tooth.value, {a: 0.0 for a in _AXES})
        for axis in _AXES:
            bucket[axis] += getattr(delta, axis)
    return totals


def _correctness_review(
    plan: TreatmentPlan, findings: list, generated
) -> tuple[CorrectnessVerdict, PipelineStep, list[Check], dict]:
    cap_violations = [f.title for f in findings if "exceeds configured" in f.title]
    collision_count = sum(1 for f in findings if "bounds overlap" in f.title)
    moved = {delta.tooth.value for stage in plan.stages for delta in stage.deltas}
    fixed_moved = sorted(moved & {control.tooth.value for control in plan.fixed_teeth})
    excluded_moved = sorted(moved & {e.tooth.value for e in plan.movement_exclusions})
    contiguous = [s.index for s in plan.stages] == list(range(len(plan.stages)))

    metrics = {
        "cap_violations": len(cap_violations),
        "fixed_teeth_moved": fixed_moved,
        "excluded_teeth_moved": excluded_moved,
        "collision_count": collision_count,
    }
    if not plan.stages:
        step = PipelineStep(name="correctness-review", status="skipped", detail="No staging produced.")
        return "NOT_APPLICABLE", step, [], metrics

    checks = [
        Check(name="caps-respected", passed=not cap_violations,
              detail=f"{len(cap_violations)} per-stage cap violation(s)"),
        Check(name="fixed-teeth-unmoved", passed=not fixed_moved,
              detail=f"fixed teeth moved: {', '.join(fixed_moved) or 'none'}"),
        Check(name="exclusions-respected", passed=not excluded_moved,
              detail=f"excluded teeth moved: {', '.join(excluded_moved) or 'none'}"),
        _targets_reached_check(plan, generated),
        Check(name="stages-contiguous", passed=contiguous,
              detail="stage indexes are contiguous from 0" if contiguous else "non-contiguous stages"),
        Check(name="scale-confirmed", passed=plan.scale_confirmed, severity="warning",
              detail="scan units confirmed" if plan.scale_confirmed else "units unverified; caps not in mm"),
        Check(name="collisions-checked", passed=True, severity="info",
              detail=f"{collision_count} crown-bounds overlap(s) reported"
                     + ("" if plan.tooth_meshes else "; no segmented teeth, overlap check is vacuous")),
    ]
    verdict: CorrectnessVerdict = "ISSUES" if any(
        c.severity == "gate" and not c.passed for c in checks
    ) else "CONSISTENT"
    failed = [c.name for c in checks if c.severity == "gate" and not c.passed]
    detail = "all gate checks passed" if verdict == "CONSISTENT" else f"failed: {', '.join(failed)}"
    step = PipelineStep(name="correctness-review",
                        status="ok" if verdict == "CONSISTENT" else "warning", detail=detail)
    return verdict, step, checks, metrics


def _model_review(
    request: GenerateRequest,
    plan: TreatmentPlan,
    provider: ModelProvider | None,
) -> tuple[list[dict], PipelineStep]:
    connector = connector_for(request.provider if provider is None else getattr(provider, "name", "local"))
    if provider is None and connector.kind == "local":
        return [], PipelineStep(
            name="model-review", status="skipped", detail="Local/offline; no external review requested."
        )
    if provider is None and not request.share_acknowledged:
        return [], PipelineStep(
            name="model-review",
            status="skipped",
            detail=f"{connector.label} review needs the external-agent acknowledgement; skipped.",
        )
    used = provider
    if used is None:
        try:
            used = build_chat_provider(
                connector.kind, model=request.model, api_key=request.api_key, endpoint=request.endpoint
            )
        except ValueError as exc:
            return [], PipelineStep(name="model-review", status="warning", detail=str(exc))
    try:
        result = request_advisory(plan, used, notes=request.notes)
    except Exception as exc:  # noqa: BLE001 - provider failures become user-facing data
        return [], PipelineStep(name="model-review", status="warning", detail=f"review failed: {exc}")
    findings = [f.model_dump(mode="json") for f in result.accepted]
    detail = f"{len(findings)} linted advisory finding(s); {len(result.rejected)} rejected by lint."
    if result.parse_error:
        detail = f"unparseable advisory: {result.parse_error}"
    return findings, PipelineStep(name="model-review", detail=detail)


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

    verdict, correctness_step, checks, metrics = _correctness_review(
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
