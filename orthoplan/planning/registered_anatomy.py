"""Resolve anatomy through its own quality-gated rigid registration, never a different study."""

import math
from orthoplan.model.geometry import apply_affine, apply_affine_direction, invert_affine
from orthoplan.model.registration_gate import gate_registration


def anatomy_registration(plan, anatomy):
    for registration in plan.registrations:
        if (
            registration.id != anatomy.registration_id
            or registration.target_cbct_record_id != anatomy.source_cbct_record_id
        ):
            continue
        if not gate_registration(registration).open:
            return None
        return registration if rigid_matrix(registration.matrix) else None
    return None


def rigid_matrix(matrix):
    if not all(math.isfinite(v) for row in matrix for v in row):
        return False
    r = [row[:3] for row in matrix[:3]]
    if any(
        abs(sum(r[k][i] * r[k][j] for k in range(3)) - float(i == j)) > 1e-6
        for i in range(3)
        for j in range(3)
    ):
        return False
    determinant = (
        r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
        - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
        + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0])
    )
    return abs(determinant - 1) < 1e-6


def scan_space_pair(plan, root, axis):
    if (
        root.registration_id != axis.registration_id
        or root.source_cbct_record_id != axis.source_cbct_record_id
    ):
        return None
    registration = anatomy_registration(plan, root)
    if registration is None:
        return None
    inverse = invert_affine(registration.matrix)
    if inverse is None:
        return None
    return (
        root.model_copy(
            update={"centerline": [apply_affine(inverse, point) for point in root.centerline]}
        ),
        axis.model_copy(
            update={
                "origin_mm": apply_affine(inverse, axis.origin_mm),
                "direction": apply_affine_direction(inverse, axis.direction),
            }
        ),
    )
