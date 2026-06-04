"""Model advisory layer (Phase 5).

Untrusted model output is parsed into a strict schema, converted to
``Finding(provenance=MODEL)``, and run through the SAME ``lint_finding`` gate as
deterministic findings via ``quarantine_findings`` - so a malformed or unsafe
advisory is rejected, never crashes, and never renders without the advisory
prefix.

This layer is entirely opt-in: it only runs when a caller passes a provider. The
default evaluation path (``api.evaluate_plan``) never invokes a model.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    LintRejection,
    quarantine_findings,
)
from orthoplan.evaluation.prompt import build_advisory_request
from orthoplan.evaluation.providers.base import ModelProvider
from orthoplan.model.plan import TreatmentPlan


class AdvisoryItem(BaseModel):
    """One model-proposed finding, before linting.

    ``category`` accepts any finding category (including ``mechanics``) so that a
    disallowed category is caught by the lint gate per-item rather than failing
    the whole batch at schema time.
    """

    severity: Literal["info", "notice", "warning"] = "notice"
    category: Literal["consistency", "mechanics", "data_gap", "education", "clinician_question"] = (
        "data_gap"
    )
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    data_gap: str | None = None
    clinician_question: str | None = None
    reference: str | None = None


class AdvisoryResponse(BaseModel):
    findings: list[AdvisoryItem] = Field(default_factory=list)


class AdvisoryResult(BaseModel):
    """Outcome of an advisory run. Never raised; always returned."""

    accepted: list[Finding] = Field(default_factory=list)
    rejected: list[LintRejection] = Field(default_factory=list)
    parse_error: str | None = None
    model: str | None = None
    provider: str | None = None


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if "```" in stripped:
        block = stripped.split("```")[1]
        if block.lstrip().lower().startswith("json"):
            block = block.lstrip()[4:]
        return block.strip()
    return stripped


def parse_advisory(text: str) -> tuple[AdvisoryResponse | None, str | None]:
    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "advisory must be a JSON object"
    try:
        return AdvisoryResponse.model_validate(data), None
    except ValidationError as exc:
        return None, f"schema mismatch: {exc.error_count()} error(s)"


def _to_finding(item: AdvisoryItem) -> Finding:
    return Finding(
        severity=FindingSeverity(item.severity),
        category=FindingCategory(item.category),
        provenance=FindingProvenance.MODEL,
        title=item.title,
        message=item.message,
        data_gap=item.data_gap,
        clinician_question=item.clinician_question,
        reference=item.reference,
    )


def request_advisory(plan: TreatmentPlan, provider: ModelProvider) -> AdvisoryResult:
    """Run the advisory layer for a plan against a provider. Never raises on bad
    model output; parse and lint failures are returned as data."""

    response = provider.complete(build_advisory_request(plan))
    parsed, error = parse_advisory(response.text)
    if parsed is None:
        return AdvisoryResult(parse_error=error, model=response.model, provider=response.provider)
    accepted, rejected = quarantine_findings([_to_finding(item) for item in parsed.findings])
    return AdvisoryResult(
        accepted=accepted,
        rejected=rejected,
        model=response.model,
        provider=response.provider,
    )
