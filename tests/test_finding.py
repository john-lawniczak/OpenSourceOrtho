from __future__ import annotations

import pytest

from orthoplan.evaluation import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)


def test_rejects_verdict_words() -> None:
    with pytest.raises(ValueError, match="banned verdict"):
        Finding(
            severity=FindingSeverity.INFO,
            category=FindingCategory.EDUCATION,
            provenance=FindingProvenance.MODEL,
            title="Plan looks safe",
            message="This should not pass.",
        )


def test_warning_requires_data_gap_and_clinician_question() -> None:
    finding = Finding(
        severity=FindingSeverity.WARNING,
        category=FindingCategory.DATA_GAP,
        provenance=FindingProvenance.RULE,
        title="Root data unavailable",
        message="The plan cannot assess root position because CBCT data is unavailable.",
    )

    with pytest.raises(ValueError, match="data gap"):
        lint_finding(finding)


def test_model_rendering_is_advisory() -> None:
    finding = Finding(
        severity=FindingSeverity.NOTICE,
        category=FindingCategory.DATA_GAP,
        provenance=FindingProvenance.MODEL,
        title="Limited data",
        message="No CBCT data was declared.",
    )

    assert finding.render().startswith("[ADVISORY - unverified]")

