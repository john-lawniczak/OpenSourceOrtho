"""Rotated, translated CBCT studies must not move or orient scan-space roots incorrectly."""

import pytest
from orthoplan.model.anatomy import ToothAxis, ReviewStatus
from orthoplan.model.geometry import apply_affine, apply_affine_direction
from orthoplan.planning.biomechanics import trusted_movement_frames
from orthoplan.evaluation.rules.root_bone import _trusted_root_points, root_bone_review
from test_root_bone import _ready_plan, _root

MATRIX = [[0, -1, 0, 10], [1, 0, 0, 20], [0, 0, 1, 30], [0, 0, 0, 1]]


def plan_with_patient_space_anatomy():
    root = _root("11", 0)
    root.centerline = [apply_affine(MATRIX, p) for p in root.centerline]
    plan = _ready_plan([root], teeth=("11",))
    plan.registrations[0].matrix = MATRIX
    plan.derived_anatomy.tooth_axes = [
        ToothAxis(
            tooth={"value": "11"},
            source_cbct_record_id="cb",
            registration_id="reg1",
            origin_mm=apply_affine(MATRIX, (0, 0, 0)),
            direction=apply_affine_direction(MATRIX, (0, 0, 1)),
            review_status=ReviewStatus.ACCEPTED,
        )
    ]
    return plan


def test_root_frame_returns_to_scan_space_and_translation_returns_to_patient_space():
    plan = plan_with_patient_space_anatomy()
    frame = trusted_movement_frames(plan)["11"]
    assert frame.axis.origin_mm == pytest.approx((0, 0, 0))
    assert frame.root.centerline[-1] == pytest.approx((0, 0, -10))
    assert frame.center_of_resistance == pytest.approx((0, 0, -10 / 3))
    points = _trusted_root_points(plan, {"11": (2, 0, 0)})["11"]
    assert points[0] == pytest.approx((10, 22, 30))


def test_unrelated_registration_cannot_unlock_anatomy():
    plan = plan_with_patient_space_anatomy()
    plan.derived_anatomy.roots[0].registration_id = "missing"
    assert trusted_movement_frames(plan) == {}
    assert any("own quality-gated" in f.message for f in root_bone_review(plan).findings)


@pytest.mark.parametrize(
    "matrix",
    [
        [[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[float("nan"), 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    ],
)
def test_scaled_reflected_and_nonfinite_frames_are_not_used(matrix):
    plan = plan_with_patient_space_anatomy()
    plan.registrations[0].matrix = matrix
    assert trusted_movement_frames(plan) == {}
