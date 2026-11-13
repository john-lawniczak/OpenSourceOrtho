"""Optional private sample goals do not become movement-plan data."""
import json

from orthoplan.plan_brief import sample_plan_brief_payload


def test_optional_private_brief_is_absent_in_filtered_installations(tmp_path):
    assert sample_plan_brief_payload(tmp_path) == {"ok": True, "available": False, "text": ""}
    folder = tmp_path / "private"
    folder.mkdir()
    path = folder / "plan-brief.json"
    path.write_text(json.dumps({"schema": "ortho-plan-brief-v1", "text": "- Discuss tooth shape"}))
    assert sample_plan_brief_payload(tmp_path) == {"ok": True, "available": True, "text": "- Discuss tooth shape"}
    for invalid in ["broken", "[]", json.dumps({"schema": "wrong", "text": "notes"}),
                    json.dumps({"schema": "ortho-plan-brief-v1", "text": "x" * 8001})]:
        path.write_text(invalid)
        assert not sample_plan_brief_payload(tmp_path)["ok"]


def test_explicit_focus_teeth_are_validated_and_optional(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir()
    path = folder / "plan-brief.json"
    record = {"schema": "ortho-plan-brief-v1", "text": "Discussion goals", "focus_teeth": ["12", "22", "31"]}
    path.write_text(json.dumps(record))
    assert sample_plan_brief_payload(tmp_path)["focus_teeth"] == ["12", "22", "31"]
    for invalid in [["99"], [12], "12,22"]:
        path.write_text(json.dumps({**record, "focus_teeth": invalid}))
        assert not sample_plan_brief_payload(tmp_path)["ok"]
