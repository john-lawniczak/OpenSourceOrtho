from __future__ import annotations

import json

from orthoplan.evaluation.advisory import request_advisory
from orthoplan.evaluation.prompt import build_advisory_request
from orthoplan.evaluation.providers.base import ModelResponse
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan


class FakeProvider:
    """A provider that returns a canned response, ignoring the request."""

    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, request) -> ModelResponse:  # noqa: ANN001 - test stub
        return ModelResponse(text=self._text, model="fake-1", provider=self.name)


def _plan() -> TreatmentPlan:
    return TreatmentPlan(
        id="advisory",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )


def _advise(payload: object) -> object:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return request_advisory(_plan(), FakeProvider(text))


def test_valid_advisory_is_accepted_and_prefixed() -> None:
    result = _advise(
        {
            "findings": [
                {"severity": "notice", "category": "data_gap", "title": "No CBCT",
                 "message": "No CBCT was declared, so root position is unknown."},
                {"severity": "info", "category": "education", "title": "Staging note",
                 "message": "Smaller per-stage steps are commonly described in the literature."},
            ]
        }
    )
    assert result.parse_error is None
    assert len(result.accepted) == 2
    assert not result.rejected
    assert all(f.provenance == "MODEL" for f in result.accepted)
    assert all(f.render().startswith("[ADVISORY - unverified]") for f in result.accepted)


def test_verdict_language_is_rejected_by_lint() -> None:
    result = _advise(
        {"findings": [{"severity": "info", "category": "education",
                       "title": "Assessment", "message": "This plan looks safe to proceed."}]}
    )
    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "verdict" in result.rejected[0].reason


def test_model_mechanics_finding_is_rejected() -> None:
    result = _advise(
        {"findings": [{"severity": "notice", "category": "mechanics",
                       "title": "Cap", "message": "Movement is large.", "reference": "x"}]}
    )
    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "mechanics" in result.rejected[0].reason


def test_warning_without_required_fields_is_rejected() -> None:
    result = _advise(
        {"findings": [{"severity": "warning", "category": "data_gap",
                       "title": "Missing data", "message": "Roots are unavailable."}]}
    )
    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "data gap" in result.rejected[0].reason


def test_mixed_batch_accepts_good_quarantines_bad() -> None:
    result = _advise(
        {"findings": [
            {"severity": "notice", "category": "data_gap", "title": "ok",
             "message": "No periodontal status was declared."},
            {"severity": "info", "category": "education", "title": "bad",
             "message": "The patient is a good candidate for aligners."},
        ]}
    )
    assert len(result.accepted) == 1
    assert len(result.rejected) == 1


def test_fenced_json_is_parsed() -> None:
    fenced = "```json\n" + json.dumps(
        {"findings": [{"severity": "info", "category": "education", "title": "t",
                       "message": "An observational educational note."}]}
    ) + "\n```"
    result = _advise(fenced)
    assert result.parse_error is None
    assert len(result.accepted) == 1


def test_invalid_json_yields_parse_error_not_crash() -> None:
    result = _advise("the model rambled instead of returning JSON")
    assert result.parse_error is not None
    assert result.accepted == []


def test_schema_mismatch_is_reported() -> None:
    result = _advise({"findings": [{"severity": "bogus", "category": "data_gap",
                                    "title": "t", "message": "m"}]})
    assert result.parse_error is not None
    assert "schema" in result.parse_error


def test_advisory_request_injects_boundary_caps_and_schema() -> None:
    request = build_advisory_request(_plan())
    assert "must not approve" in request.system
    assert "verdict words" in request.system
    assert "movement_caps" in request.prompt
    assert "data_availability" in request.prompt


def test_advisory_request_appends_user_notes_without_relaxing_boundary() -> None:
    request = build_advisory_request(_plan(), notes="Align the lateral incisors 12 and 22.")
    assert "User focus" in request.prompt
    assert "lateral incisors 12 and 22" in request.prompt
    # The notes never weaken the system boundary.
    assert "must not approve" in request.system

    # Empty/whitespace notes add nothing.
    assert "User focus" not in build_advisory_request(_plan(), notes="   ").prompt
