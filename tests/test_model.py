from __future__ import annotations

import pytest

from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan


def test_stage_rejects_duplicate_teeth() -> None:
    tooth = ToothId(value="11")

    with pytest.raises(ValueError, match="duplicate tooth"):
        Stage(
            index=0,
            deltas=[
                ToothDelta(tooth=tooth, arch="maxillary"),
                ToothDelta(tooth=tooth, arch="maxillary"),
            ],
        )


def test_plan_stage_indexes_must_be_contiguous() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        TreatmentPlan(id="example", stages=[Stage(index=1)])

