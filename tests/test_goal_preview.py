"""A provider can propose a bounded edit; it cannot commit or retarget it."""
import json

import pytest

from orthoplan.goal_preview import preview_goal_payload
from orthoplan.ai_chat import answer_chat_payload
from orthoplan.ai_chat_stream import chat_stream_events
from orthoplan.evaluation.providers.base import ModelResponse
from orthoplan.model import TreatmentPlan


def payload(**extra):
    plan = TreatmentPlan.model_validate({
        "id": "preview", "scans": [{"asset": {"id": "scan", "format": "stl", "units": "mm", "vertex_count": 3, "face_count": 1}}],
        "mesh_assets": [{"id": "tooth-11", "format": "stl", "units": "mm", "vertex_count": 3, "face_count": 1}],
        "tooth_meshes": [{"tooth": {"value": "11"}, "mesh_asset_id": "tooth-11", "reviewed": True}],
        "stages": [{"index": 0, "deltas": [{"tooth": {"value": "11"}, "translate_x_mm": .2}]},
                   {"index": 1, "deltas": [{"tooth": {"value": "11"}, "translate_x_mm": .2}]}],
    })
    return {"plan": plan.model_dump(mode="json"), "selected_tooth": "11", "message": "move 0.2 mm right", **extra}


class Provider:
    name = "openai"

    def __init__(self, text):
        self.text, self.calls = text, 0

    def complete(self, request):
        self.calls += 1
        return ModelResponse(text=self.text, model="fake", provider=self.name)


def test_preview_preserves_input_and_adds_to_cumulative_target():
    request = payload()
    original = json.dumps(request)
    result = preview_goal_payload(request)
    assert result["ok"]
    assert json.dumps(request) == original
    assert result["baseline_hash"]
    values = [d["translate_x_mm"] for s in result["plan"]["stages"] for d in s["deltas"]]
    assert sum(values) == pytest.approx(.6)
    assert max(values) <= .25
    assert result["plan"]["stages"][:2] == request["plan"]["stages"]
    assert all(d["source"] == "model" for s in result["plan"]["stages"][2:] for d in s["deltas"])


@pytest.mark.parametrize("change", ["unverified", "cm", "unreviewed", "unsegmented", "held", "excluded"])
def test_edit_prerequisites_fail_before_provider_call(change):
    request = payload(share_acknowledged=True)
    plan = request["plan"]
    if change in {"unverified", "cm"}:
        plan["scans"][0]["asset"]["units"] = change
    elif change == "unreviewed":
        plan["tooth_meshes"][0]["reviewed"] = False
    elif change == "unsegmented":
        plan["tooth_meshes"] = []
    elif change == "held":
        plan["fixed_teeth"] = [{"tooth": {"value": "11"}}]
    else:
        plan["movement_exclusions"] = [{"tooth": {"value": "11"}, "axes": ["translate_x"]}]
    provider = Provider("{}")
    assert not preview_goal_payload(request, provider=provider)["ok"]
    assert provider.calls == 0


@pytest.mark.parametrize("goal", [
    {"tooth": "12", "x_mm": .2, "explanation": "Different tooth."},
    {"tooth": "11", "x_mm": 5, "explanation": "Large shift."},
    {"tooth": "11", "x_mm": .2, "z_mm": .3, "explanation": "Extra axis."},
    {"tooth": "11", "x_mm": .2, "explanation": "This is safe and approved."},
    {"tooth": "11", "x_mm": float("nan"), "explanation": "Invalid."},
])
def test_untrusted_provider_output_is_rejected(goal):
    provider = Provider(json.dumps(goal))
    assert not preview_goal_payload(payload(share_acknowledged=True), provider=provider)["ok"]


def test_consent_and_ambiguous_intent_do_not_move_teeth():
    provider = Provider('{}')
    assert not preview_goal_payload(payload(), provider=provider)["ok"]
    assert provider.calls == 0
    assert not preview_goal_payload(payload(message="fix my bite"))["ok"]
    provider = Provider('{"tooth":"11","explanation":"Which direction and distance?"}')
    result = preview_goal_payload(payload(share_acknowledged=True), provider=provider)
    assert result["ok"] and "plan" not in result and result["clarification"]


def test_manual_nudge_never_calls_external_provider_and_limit_is_cumulative():
    provider = Provider('{}')
    result = preview_goal_payload(payload(adjustment={"x_mm": -.2}), provider=provider)
    assert result["ok"] and provider.calls == 0
    result = preview_goal_payload(payload(adjustment={"x_mm": 3.8}))
    assert not result["ok"]


def test_chat_model_text_is_linted_before_display():
    provider = Provider("The plan is approved.")
    result = answer_chat_payload(payload(), provider=provider)
    assert not result["ok"]
    assert "approved" not in json.dumps(result)


def test_single_tooth_preview_preserves_every_authored_stage_and_control():
    request = payload()
    stages = request["plan"]["stages"]
    # A net-zero excursion must not disappear when another tooth is edited.
    stages[0]["deltas"].append({"tooth": {"value": "21"}, "translate_x_mm": .2})
    stages[1]["deltas"].append({"tooth": {"value": "21"}, "translate_x_mm": -.2})
    request["plan"]["attachments"] = [{"tooth": {"value": "21"}, "stage_start": 1, "stage_end": 1}]
    original = TreatmentPlan.model_validate(request["plan"]).model_dump(mode="json")
    result = preview_goal_payload(request)
    assert result["ok"]
    assert result["plan"]["stages"][:2] == original["stages"]
    assert result["plan"]["attachments"] == original["attachments"]
    assert all(d["tooth"]["value"] == "11" for s in result["plan"]["stages"][2:] for d in s["deltas"])


def test_tiny_caps_reject_excessive_preview_work():
    request = payload()
    request["plan"]["settings"]["movement_caps"]["default"]["linear_mm"] = 1e-12
    result = preview_goal_payload(request)
    assert not result["ok"]
    assert "512" in result["errors"][0]


def test_other_tooth_control_horizon_does_not_expand_preview_search():
    request = payload()
    request["plan"]["fixed_teeth"] = [{"tooth": {"value": "21"}, "stage_end": 1000000000}]
    result = preview_goal_payload(request)
    assert result["ok"]
    assert len(result["plan"]["stages"]) == 3
    assert result["plan"]["fixed_teeth"][0]["stage_end"] == 1000000000
