"""Regressions for the tooth comparison that previously got a stock plan summary."""
import pytest

from orthoplan.ai_chat import answer_chat_payload
from orthoplan.ai_chat_local import local_answer
from orthoplan.ai_chat_stream import chat_stream_events
from orthoplan.evaluation.providers.base import ModelResponse


QUESTION = "IS TOOTH 23 BIGGER THAN say 13, should it be fied down?"


def payload(**overrides):
    return {"plan": {"id": "workspace", "stages": []}, "message": QUESTION,
            "provider": "local", "context_scope": "full_plan", **overrides}


@pytest.mark.parametrize("question", [QUESTION, "Is tooth 23 wider than 13? Should it be filed down?",
                                    "Should I shave tooth 23?", "Compare crown height of 13 and 23"])
def test_workspace_comparison_answers_topic_without_claiming_case_access(question):
    result = answer_chat_payload(payload(message=question))
    assert result["ok"]
    answer = result["session"]["messages"][-1]["content"]
    assert "actual size" in answer
    assert "select USER_ONE" in answer
    assert "same scan" in answer
    assert "offline" in answer
    assert "stage(s)" not in answer and "first deterministic signal" not in answer
    assert "selected_case" not in result["context"]


def test_selected_case_explains_missing_measurements_despite_unequal_face_counts(monkeypatch):
    context = {"plan_id": "USER_ONE-scan-review", "plan_hash": "fixture",
               "selected_case": {"saved_baseline_labels": [
                   {"labeled_faces_by_fdi": {"23": 10000, "13": 5000}}]}}
    monkeypatch.setattr("orthoplan.ai_chat.user_one_chat_context", lambda: context)
    result = answer_chat_payload(payload(case_source="user_one"))
    answer = result["session"]["messages"][-1]["content"]
    assert "23 is the upper left canine" in answer
    assert "13 is the upper right canine" in answer
    assert "Label face counts are not tooth sizes" in answer
    assert "no measured crown widths or heights" in answer
    assert "Enamel removal is irreversible" in answer
    assert "Don't file it yourself" in answer
    assert "select USER_ONE" not in answer
    assert "10000" not in answer and "5000" not in answer


def test_unrelated_size_or_file_question_does_not_trigger_dental_response():
    for question in ["Why is the file size bigger?", "Make the chat window wider",
                     "Explain stage 13", "What are the limitations?"]:
        answer = local_answer(question, {})
        assert "not AI reasoning" in answer
        assert "Enamel" not in answer and "actual size" not in answer


def test_exact_question_survives_streaming():
    events = list(chat_stream_events(payload()))
    assert events[-1]["event"] == "done"
    assert "Enamel removal is irreversible" in events[-1]["data"]["session"]["messages"][-1]["content"]


class Provider:
    name = "openai"

    def __init__(self, answer):
        self.answer = answer

    def complete(self, request):
        self.request = request
        return ModelResponse(text=self.answer, model="test", provider=self.name)


def test_external_prompt_addresses_comparison_and_preserves_lint_gate():
    provider = Provider("No individual crown dimensions were supplied.")
    result = answer_chat_payload(payload(), provider=provider)
    assert result["ok"]
    assert QUESTION in provider.request.prompt
    assert "Address the user's actual question first" in provider.request.system
    assert "chat displays plain text" in provider.request.system
    assert "scan-axis bounding boxes" in provider.request.system
    assert "Label face counts" in provider.request.system
    assert "Do not prescribe removal or DIY steps" in provider.request.system
    provider.answer = "Tooth 23 is safe to file down."
    rejected = answer_chat_payload(payload(), provider=provider)
    assert not rejected["ok"]
    assert provider.answer not in str(rejected)
