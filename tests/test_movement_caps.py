from __future__ import annotations

from orthoplan.evaluation.rules import evaluate_movement_caps
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan


def test_movement_cap_rule_flags_excess_stage_movement() -> None:
    plan = TreatmentPlan(
        id="caps-test",
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        arch="maxillary",
                        translate_x_mm=0.30,
                    )
                ],
            )
        ],
    )

    findings = evaluate_movement_caps(plan)

    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].data_gap
    assert findings[0].clinician_question


def test_movement_cap_rule_allows_configured_caps() -> None:
    plan = TreatmentPlan(
        id="caps-test",
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        arch="maxillary",
                        translate_x_mm=0.20,
                    )
                ],
            )
        ],
    )

    assert evaluate_movement_caps(plan) == []
