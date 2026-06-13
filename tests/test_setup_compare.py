from __future__ import annotations

from orthoplan.model.clinical import Attachment, FixedTooth
from orthoplan.model.plan import Stage, ToothDelta, TreatmentPlan
from orthoplan.setup_compare import (
    compare_setups,
    compare_setups_payload,
    live_restage_comparison,
)


def _plan(plan_id: str, x: float, *, stages: int = 1) -> TreatmentPlan:
    deltas = [ToothDelta(tooth={"system": "FDI", "value": "11"}, translate_x_mm=x)]
    stage_list = [Stage(index=0, deltas=deltas)]
    if stages > 1:
        stage_list.append(
            Stage(
                index=1,
                deltas=[ToothDelta(tooth={"system": "FDI", "value": "21"}, translate_y_mm=0.2)],
            )
        )
    return TreatmentPlan(id=plan_id, stages=stage_list)


def test_compare_setups_reports_changed_teeth_and_controls() -> None:
    before = _plan("before", 0.2)
    after = _plan("after", 0.5, stages=2).model_copy(
        update={
            "attachments": [Attachment(tooth={"system": "FDI", "value": "11"})],
            "fixed_teeth": [FixedTooth(tooth={"system": "FDI", "value": "16"})],
        }
    )

    comparison = compare_setups(before, after)

    assert comparison.stage_count_delta == 1
    assert comparison.added_teeth == ["21"]
    assert comparison.attachment_count_delta == 1
    assert comparison.fixed_tooth_count_delta == 1
    diff = comparison.changed_teeth[0]
    assert diff.tooth == "11"
    assert diff.delta["translate_x_mm"] == 0.3


def test_live_restage_comparison_restages_edited_authored_target() -> None:
    before = _plan("before", 0.2)
    edited = _plan("edited", 0.6)

    result = live_restage_comparison(before, edited)

    assert result.source == "authored"
    assert result.comparison.after_stage_count >= 1
    assert result.restaged_timeline_days >= result.before_timeline_days
    assert result.comparison.changed_teeth[0].delta["translate_x_mm"] == 0.4


def test_compare_payload_returns_validation_errors() -> None:
    result = compare_setups_payload({"before": {"id": "ok"}, "after": {"title": "missing id"}})

    assert result["ok"] is False
    assert result["errors"]
