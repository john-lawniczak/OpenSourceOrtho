from __future__ import annotations

import pytest

from orthoplan.model import Arch, Stage, ToothDelta, ToothId, TreatmentPlan


def test_stage_rejects_duplicate_teeth() -> None:
    tooth = ToothId(value="11")

    with pytest.raises(ValueError, match="duplicate tooth"):
        Stage(index=0, deltas=[ToothDelta(tooth=tooth), ToothDelta(tooth=tooth)])


def test_plan_stage_indexes_must_be_contiguous() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        TreatmentPlan(id="example", stages=[Stage(index=1)])


def test_arch_is_derived_from_fdi_quadrant() -> None:
    assert ToothId(value="11").arch is Arch.MAXILLARY
    assert ToothId(value="31").arch is Arch.MANDIBULAR
    assert ToothDelta(tooth=ToothId(value="46")).arch is Arch.MANDIBULAR


def test_invalid_fdi_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        ToothId(value="99")  # quadrant 9 and position 9 are both invalid
    with pytest.raises(ValueError):
        ToothId(value="1")  # must be two digits


def test_mixed_coordinate_frame_is_rejected() -> None:
    with pytest.raises(ValueError, match="coordinate frame"):
        TreatmentPlan(
            id="frame",
            stages=[
                Stage(
                    index=0,
                    deltas=[ToothDelta(tooth=ToothId(value="11"), coordinate_frame="other")],
                )
            ],
        )
