from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class FindingSeverity(StrEnum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"


class FindingCategory(StrEnum):
    CONSISTENCY = "consistency"
    MECHANICS = "mechanics"
    DATA_GAP = "data_gap"
    EDUCATION = "education"
    CLINICIAN_QUESTION = "clinician_question"


class FindingProvenance(StrEnum):
    RULE = "RULE"
    MODEL = "MODEL"


# Verdict language is matched with word boundaries (so "unsafe"/"unacceptable"
# are not falsely flagged) and as whole phrases for multiword verdicts. The set
# includes positive-sounding phrasings that imply clinical clearance without
# using the obvious verdict words.
VERDICT_PATTERNS = (
    r"approved",
    r"acceptable",
    r"cleared",
    r"safe",
    r"suitable",
    r"healthy",
    r"ready for treatment",
    r"clinically acceptable",
    r"good candidate",
    r"within normal limits",
    r"no concerns",
)
_VERDICT_RE = re.compile(
    r"\b(" + "|".join(VERDICT_PATTERNS) + r")\b", flags=re.IGNORECASE
)

# All free-text fields are scanned, not just title/message, so a model cannot
# smuggle verdict language into a clinician_question or reference.
_TEXT_FIELDS = ("title", "message", "data_gap", "clinician_question", "reference")


class FindingLintError(ValueError):
    """Raised when a finding violates a safety-gate rule.

    Subclasses ``ValueError`` so existing callers catching ``ValueError`` keep
    working, but is distinguishable for quarantine handling.
    """


class Finding(BaseModel):
    severity: FindingSeverity
    category: FindingCategory
    provenance: FindingProvenance
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    code: str | None = None
    data_gap: str | None = None
    clinician_question: str | None = None
    reference: str | None = None

    def render(self) -> str:
        prefix = "[ADVISORY - unverified] " if self.provenance == FindingProvenance.MODEL else ""
        return f"{prefix}{self.severity.value.upper()}: {self.title}\n{self.message}"


class LintRejection(BaseModel):
    finding: Finding
    reason: str


def _verdict_violation(finding: Finding) -> str | None:
    for field in _TEXT_FIELDS:
        value = getattr(finding, field)
        if value and (match := _VERDICT_RE.search(value)):
            return f"{field} contains banned verdict language: {match.group(0)!r}"
    return None


def lint_finding(finding: Finding) -> Finding:
    """The single safety gate. Construction is not the final gate.

    Raises ``FindingLintError`` on violation. Use ``quarantine_findings`` to
    reject invalid findings without crashing the pipeline.
    """

    if violation := _verdict_violation(finding):
        raise FindingLintError(violation)

    if finding.provenance == FindingProvenance.MODEL and finding.category == FindingCategory.MECHANICS:
        raise FindingLintError(
            "model-sourced mechanics findings are forbidden; deterministic rules own mechanics"
        )

    if finding.severity == FindingSeverity.WARNING:
        if not finding.data_gap:
            raise FindingLintError("warning findings must include a data gap")
        if not finding.clinician_question:
            raise FindingLintError("warning findings must include a follow-up question")

    if finding.category == FindingCategory.MECHANICS and not finding.reference:
        raise FindingLintError(
            "mechanics findings with numeric thresholds must reference a cap or citation"
        )

    return finding


def quarantine_findings(findings: list[Finding]) -> tuple[list[Finding], list[LintRejection]]:
    """Lint a batch; return (accepted, rejected) without raising.

    Use this for untrusted (model-sourced) findings so a single bad finding
    cannot crash display or export.
    """

    accepted: list[Finding] = []
    rejected: list[LintRejection] = []
    for finding in findings:
        try:
            accepted.append(lint_finding(finding))
        except FindingLintError as exc:
            rejected.append(LintRejection(finding=finding, reason=str(exc)))
    return accepted, rejected
