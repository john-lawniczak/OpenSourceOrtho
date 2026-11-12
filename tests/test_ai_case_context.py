"""Selected case context remains explicit, bounded and separate from a user's plan."""
import base64
import json

from orthoplan.ai_case_context import user_one_chat_context
from orthoplan.ai_chat import answer_chat_payload
from orthoplan.evaluation.providers.base import ModelResponse
from orthoplan.region_corrections import baseline_source, save_baseline_corrections


class CaptureProvider:
    name = "openai"

    def complete(self, request):
        self.request = request
        return ModelResponse(text="These are draft label summaries, not a surface inspection.", model="test", provider=self.name)


def test_user_one_has_scan_records_latest_labels_and_no_raw_data(monkeypatch, tmp_path):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    source = baseline_source("upper")
    labels = bytes([21, 22]) + bytes(source["face_count"] - 2)
    corrections = {"schema": "ortho-region-corrections-v1", "source_sha256": source["sha256"],
                   "arch": "upper", "face_count": source["face_count"], "reviewed": False,
                   "provenance": "user-corrected", "labels_base64": base64.b64encode(labels).decode()}
    save_baseline_corrections({"arch": "upper", "corrections": corrections, "notes": "Front labels checked so far"})
    context = user_one_chat_context()
    case = context["selected_case"]
    assert case["dentition"]["absent_fdi"] == ["18", "28", "38", "48"]
    assert len(case["scans"]) == 8
    assert {1, 7, 18} == {s["week"] for s in case["scans"]}
    assert not any(s["private_record"] for s in case["scans"])
    annotation = case["saved_baseline_labels"][0]
    assert annotation["labeled_faces_by_fdi"] == {"21": 1, "22": 1}
    assert annotation["review_status"] == "draft" and annotation["notes"] == "Front labels checked so far"
    wire = json.dumps(context)
    assert "labels_base64" not in wire and str(tmp_path) not in wire
    assert len(wire) < 24000
    assert context["workspace_plan_included"] is False
    save_baseline_corrections({"arch": "upper", "corrections": corrections, "notes": "Updated review note"})
    assert user_one_chat_context()["selected_case"]["saved_baseline_labels"][0]["notes"] == "Updated review note"


def test_selected_case_reaches_provider_without_unrelated_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    provider = CaptureProvider()
    payload = {"plan": {"id": "unrelated-secret-plan", "title": "Separate workspace", "stages": []},
               "message": "What records exist?", "case_source": "user_one", "context_scope": "full_plan"}
    result = answer_chat_payload(payload, provider=provider)
    assert result["ok"]
    assert "initial-upper.stl" in provider.request.prompt
    assert "unrelated-secret-plan" not in provider.request.prompt
    assert result["session"]["plan_id"] == "USER_ONE-scan-review"
    regular = answer_chat_payload({**payload, "case_source": "workspace"}, provider=provider)
    assert "selected_case" not in regular["context"]
    assert "initial-upper.stl" not in provider.request.prompt
    assert not answer_chat_payload({**payload, "context_scope": "summary"}, provider=provider)["ok"]
    assert not answer_chat_payload({**payload, "case_source": "../../private"}, provider=provider)["ok"]


def test_case_context_still_requires_egress_consent(monkeypatch, tmp_path):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    result = answer_chat_payload({"plan": {"id": "empty", "stages": []}, "message": "Explain",
                                  "case_source": "user_one", "context_scope": "full_plan",
                                  "provider": "openai", "api_key": "synthetic", "share_acknowledged": False})
    assert not result["ok"]
    assert "acknowledge" in str(result["errors"])
