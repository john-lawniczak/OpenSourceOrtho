from __future__ import annotations

import pytest

from orthoplan.evaluation import (
    Finding,
    FindingCategory,
    FindingLintError,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
    quarantine_findings,
)
from orthoplan.evaluation.finding import VERDICT_PATTERNS


def _finding(**overrides: object) -> Finding:
    base = dict(
        severity=FindingSeverity.INFO,
        category=FindingCategory.EDUCATION,
        provenance=FindingProvenance.MODEL,
        title="Limited data",
        message="No CBCT data was declared.",
    )
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


def test_construction_is_not_the_gate() -> None:
    # Construction no longer raises on verdict language; lint is the gate.
    finding = _finding(title="Plan looks safe")
    with pytest.raises(FindingLintError, match="verdict"):
        lint_finding(finding)


def test_verdict_scan_covers_all_text_fields() -> None:
    finding = _finding(clinician_question="Is the patient a good candidate?")
    with pytest.raises(FindingLintError, match="clinician_question"):
        lint_finding(finding)


@pytest.mark.parametrize("field", ["title", "message", "data_gap", "clinician_question", "reference"])
@pytest.mark.parametrize("verdict", VERDICT_PATTERNS)
def test_verdict_language_is_rejected_in_every_text_field(field: str, verdict: str) -> None:
    finding = _finding(**{field: f"Observed finding: {verdict.upper()}."})
    with pytest.raises(FindingLintError, match=field):
        lint_finding(finding)


def test_quarantine_rejects_adversarial_verdict_batch_without_accepting_any() -> None:
    findings = [
        _finding(message=f"The plan is {verdict}.")
        for verdict in VERDICT_PATTERNS
    ]
    accepted, rejected = quarantine_findings(findings)
    assert accepted == []
    assert len(rejected) == len(VERDICT_PATTERNS)


def test_negated_words_are_not_falsely_flagged() -> None:
    finding = _finding(
        provenance=FindingProvenance.RULE,
        title="Movement may be unsafe to assume",
        message="This is unacceptable to infer from surface data.",
    )
    assert lint_finding(finding) is finding


def test_model_mechanics_findings_are_forbidden() -> None:
    finding = _finding(category=FindingCategory.MECHANICS, reference="caps")
    with pytest.raises(FindingLintError, match="mechanics findings are forbidden"):
        lint_finding(finding)


def test_warning_requires_data_gap_and_clinician_question() -> None:
    finding = _finding(severity=FindingSeverity.WARNING, category=FindingCategory.DATA_GAP)
    with pytest.raises(FindingLintError, match="data gap"):
        lint_finding(finding)


def test_quarantine_separates_valid_and_invalid() -> None:
    accepted, rejected = quarantine_findings(
        [
            _finding(),
            _finding(title="Plan looks safe"),
            _finding(category=FindingCategory.MECHANICS, reference="caps"),
        ]
    )
    assert len(accepted) == 1
    assert len(rejected) == 2
    assert all(rej.reason for rej in rejected)


def test_model_rendering_is_advisory() -> None:
    assert _finding(severity=FindingSeverity.NOTICE).render().startswith("[ADVISORY - unverified]")
