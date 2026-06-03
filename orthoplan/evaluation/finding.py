from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


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


VERDICT_WORDS = {
    "approved",
    "acceptable",
    "cleared",
    "safe",
    "suitable",
    "ready for treatment",
    "clinically acceptable",
}


class Finding(BaseModel):
    severity: FindingSeverity
    category: FindingCategory
    provenance: FindingProvenance
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    data_gap: str | None = None
    clinician_question: str | None = None
    reference: str | None = None

    @field_validator("title", "message")
    @classmethod
    def no_verdict_words(cls, value: str) -> str:
        lowered = value.lower()
        for word in VERDICT_WORDS:
            if word in lowered:
                raise ValueError(f"finding contains banned verdict language: {word}")
        return value

    def render(self) -> str:
        prefix = "[ADVISORY - unverified] " if self.provenance == FindingProvenance.MODEL else ""
        return f"{prefix}{self.severity.value.upper()}: {self.title}\n{self.message}"


def lint_finding(finding: Finding) -> Finding:
    if finding.severity == FindingSeverity.WARNING:
        if not finding.data_gap:
            raise ValueError("warning findings must include a data gap")
        if not finding.clinician_question:
            raise ValueError("warning findings must include a clinician question")

    if finding.category == FindingCategory.MECHANICS and not finding.reference:
        raise ValueError("mechanics findings with numeric thresholds must reference a cap or citation")

    return finding

