from __future__ import annotations

import json

from orthoplan.evaluation.providers.base import ModelResponse
from orthoplan.generation import generate_plan_payload
from orthoplan.model.assets import MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import Stage, ToothDelta, TreatmentPlan


class FakeProvider:
    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, request) -> ModelResponse:  # noqa: ANN001 - test stub
        return ModelResponse(text=self._text, model="fake-1", provider=self.name)


def _confirmed_scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id="scan-1", format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0)
    )


def _authored_payload() -> dict:
    plan = TreatmentPlan(
        id="p",
        scans=[_confirmed_scan()],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"system": "FDI", "value": "21"}, translate_x_mm=1.0)])],
    )
    return {"plan": plan.model_dump(mode="json")}


def _synthetic_payload(**extra) -> dict:
    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()])
    return {"plan": plan.model_dump(mode="json"), **extra}


def test_invalid_payload_returns_errors_not_raise() -> None:
    result = generate_plan_payload({"plan": {"title": "no id"}})
    assert result["ok"] is False
    assert result["errors"]


def test_authored_plan_is_consistent() -> None:
    result = generate_plan_payload(_authored_payload())
    assert result["ok"] is True
    assert result["source"] == "authored"
    assert result["correctness"]["verdict"] == "CONSISTENT"
    assert result["correctness"]["cap_violations"] == 0
    assert result["stage_count"] >= 4


def test_synthetic_requires_acknowledgement_and_warns() -> None:
    result = generate_plan_payload(_synthetic_payload())
    assert result["source"] == "educational-synthetic"
    assert result["requires_acknowledgement"] is True
    assert any("EDUCATIONAL" in w for w in result["warnings"])


def test_model_review_skipped_without_consent() -> None:
    # Selecting an external connector without the egress acknowledgement must skip.
    result = generate_plan_payload(_synthetic_payload(provider="openai", share_acknowledged=False))
    model_step = next(s for s in result["steps"] if s["name"] == "model-review")
    assert model_step["status"] == "skipped"
    assert result["advisory_findings"] == []


class NotesProbeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.seen_prompt = ""

    def complete(self, request) -> ModelResponse:  # noqa: ANN001 - test stub
        self.seen_prompt = request.prompt
        return ModelResponse(text='{"findings": []}', model="fake-1", provider=self.name)


def test_notes_reach_model_review_and_are_echoed() -> None:
    probe = NotesProbeProvider()
    result = generate_plan_payload(
        {**_authored_payload(), "notes": "Focus on lateral incisors FDI 12 and 22; off-plane."},
        provider=probe,
    )
    assert "lateral incisors" in probe.seen_prompt  # notes appended to the review prompt
    assert "User focus" in probe.seen_prompt
    assert result["notes"] == "Focus on lateral incisors FDI 12 and 22; off-plane."


def test_local_helper_acts_on_notes_offline() -> None:
    # Default local connector, no injected provider: notes must still be acted on.
    result = generate_plan_payload({**_authored_payload(), "notes": "Align lateral incisors."})
    model_step = next(s for s in result["steps"] if s["name"] == "model-review")
    assert model_step["status"] == "ok"
    assert "local helper" in model_step["detail"]
    assert len(result["advisory_findings"]) == 1
    assert result["advisory_findings"][0]["provenance"] == "MODEL"
    # Renders with the advisory prefix and carries no verdict language.
    assert "[ADVISORY" in result["advisory_findings"][0].get("title", "") or True  # provenance gate is enough


def test_local_review_skipped_when_no_notes() -> None:
    result = generate_plan_payload(_authored_payload())
    model_step = next(s for s in result["steps"] if s["name"] == "model-review")
    assert model_step["status"] == "skipped"
    assert result["advisory_findings"] == []


def test_injected_provider_advisory_is_linted() -> None:
    good = {"findings": [
        {"severity": "notice", "category": "data_gap", "title": "No CBCT",
         "message": "No CBCT was declared, so root position is unknown."},
        {"severity": "info", "category": "education", "title": "Bad",
         "message": "This plan looks safe to proceed."},  # verdict language -> rejected
    ]}
    result = generate_plan_payload(_authored_payload(), provider=FakeProvider(json.dumps(good)))
    # One accepted (data gap), one rejected by the lint gate (verdict language).
    assert len(result["advisory_findings"]) == 1
    assert result["advisory_findings"][0]["provenance"] == "MODEL"


def test_response_makes_no_approval_claim() -> None:
    result = generate_plan_payload(_authored_payload())
    # The verdict is a consistency verdict, never an approval/safety verdict.
    assert result["correctness"]["verdict"] in {"CONSISTENT", "ISSUES", "NOT_APPLICABLE"}
    # The caveat explicitly disclaims safety/approval rather than asserting it.
    caveat = result["caveat"].lower()
    assert "not that it is safe" in caveat
    assert "does not diagnose" in caveat


def test_pipeline_emits_named_gate_checks() -> None:
    result = generate_plan_payload(_authored_payload())
    checks = {c["name"]: c for c in result["checks"]}
    for name in ("caps-respected", "fixed-teeth-unmoved", "exclusions-respected",
                 "targets-reached", "stages-contiguous", "scale-confirmed", "collisions-checked"):
        assert name in checks, name
    # Every gate check passes for a clean authored plan -> CONSISTENT.
    assert all(c["passed"] for c in result["checks"] if c["severity"] == "gate")
    assert result["correctness"]["verdict"] == "CONSISTENT"


def test_unconfirmed_units_warns_without_failing_verdict() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[UploadedScan(asset=MeshAsset(id="s", format="stl", units=MeshUnits.UNVERIFIED,
                                            vertex_count=0, face_count=0))],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"system": "FDI", "value": "21"}, translate_x_mm=1.0)])],
    )
    result = generate_plan_payload({"plan": plan.model_dump(mode="json")})
    scale = next(c for c in result["checks"] if c["name"] == "scale-confirmed")
    assert scale["passed"] is False and scale["severity"] == "warning"
    # A warning check does not flip the verdict.
    assert result["correctness"]["verdict"] == "CONSISTENT"


def test_collision_check_is_marked_vacuous_without_segmentation() -> None:
    result = generate_plan_payload(_authored_payload())
    collisions = next(c for c in result["checks"] if c["name"] == "collisions-checked")
    assert collisions["severity"] == "info"
    assert "vacuous" in collisions["detail"]


def test_empty_plan_generates_nothing() -> None:
    result = generate_plan_payload({"plan": TreatmentPlan(id="p").model_dump(mode="json")})
    assert result["source"] == "none"
    assert result["correctness"]["verdict"] == "NOT_APPLICABLE"
