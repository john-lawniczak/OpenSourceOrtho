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
