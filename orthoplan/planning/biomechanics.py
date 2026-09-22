from __future__ import annotations

import math
from dataclasses import dataclass

from orthoplan.model.anatomy import RootGeometry, ToothAxis
from orthoplan.model.geometry import Vec3
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import root_bone_aware_ready
from orthoplan.planning.transforms import PIVOT_LABEL, ToothPose

ROOT_AWARE_PIVOT_LABEL = "root-derived center of resistance (reviewed CBCT anatomy)"


@dataclass(frozen=True)
class RootAwareMovementFrame:
    axis: ToothAxis
    root: RootGeometry
    center_of_resistance: Vec3


def movement_mode(plan: TreatmentPlan) -> dict[str, object]:
    frames = trusted_movement_frames(plan)
    root_ready = root_bone_aware_ready(plan)
    return {
        "mode": "root-aware" if frames else "crown-centroid",
        "pivot_label": ROOT_AWARE_PIVOT_LABEL if frames else PIVOT_LABEL,
        "root_bone_aware_ready": root_ready,
        "trusted_teeth": sorted(frames),
        "note": (
            "Trusted root geometry and long axes are used for tooth rotation."
            if frames
            else "Using crown-centroid visualization assumption; biomechanics cannot be assessed."
        ),
    }


def trusted_movement_frames(plan: TreatmentPlan) -> dict[str, RootAwareMovementFrame]:
    anatomy = plan.derived_anatomy
    if anatomy is None or not root_bone_aware_ready(plan):
        return {}
    roots = {root.tooth.value: root for root in anatomy.roots if root.trusted}
    axes = {axis.tooth.value: axis for axis in anatomy.tooth_axes if axis.trusted}
    frames: dict[str, RootAwareMovementFrame] = {}
    for tooth, axis in axes.items():
        root = roots.get(tooth)
        if root is None:
            continue
        center = _center_of_resistance(axis, root)
        frames[tooth] = RootAwareMovementFrame(axis=axis, root=root, center_of_resistance=center)
    return frames


def apply_pose_to_vertex(vertex: Vec3, pose: ToothPose, frame: RootAwareMovementFrame | None) -> Vec3:
    translated = (
        vertex[0] + pose.translate_x_mm,
        vertex[1] + pose.translate_y_mm,
        vertex[2] + pose.translate_z_mm,
    )
    if frame is None:
        return translated
    rotated = _rotate_root_aware(vertex, pose, frame)
    return (
        rotated[0] + pose.translate_x_mm,
        rotated[1] + pose.translate_y_mm,
        rotated[2] + pose.translate_z_mm,
    )


def _center_of_resistance(axis: ToothAxis, root: RootGeometry) -> Vec3:
    direction = _unit(axis.direction)
    if direction == (0.0, 0.0, 0.0) or not root.centerline:
        return axis.origin_mm
    apex = root.centerline[-1]
    dot = sum((apex[i] - axis.origin_mm[i]) * direction[i] for i in range(3))
    root_length = abs(dot)
    # A simple reviewed-anatomy estimate: the resistance center lies apical to
    # the crown/root origin, roughly one third of root length along the root.
    return tuple(axis.origin_mm[i] - direction[i] * root_length / 3.0 for i in range(3))  # type: ignore[return-value]


def _rotate_root_aware(vertex: Vec3, pose: ToothPose, frame: RootAwareMovementFrame) -> Vec3:
    axis = _unit(frame.axis.direction)
    if axis == (0.0, 0.0, 0.0):
        return vertex
    point = vertex
    # Tip and torque are expressed as rotations around axes perpendicular to the
    # reviewed long axis; rotation uses the reviewed long axis itself.
    lateral = _perpendicular_axis(axis)
    torque = _cross(axis, lateral)
    if pose.rotate_tip_deg:
        point = _rotate(point, frame.center_of_resistance, lateral, pose.rotate_tip_deg)
    if pose.rotate_torque_deg:
        point = _rotate(point, frame.center_of_resistance, torque, pose.rotate_torque_deg)
    if pose.rotate_rotation_deg:
        point = _rotate(point, frame.center_of_resistance, axis, pose.rotate_rotation_deg)
    return point


def _rotate(point: Vec3, origin: Vec3, axis: Vec3, degrees: float) -> Vec3:
    ux, uy, uz = _unit(axis)
    if (ux, uy, uz) == (0.0, 0.0, 0.0):
        return point
    radians = math.radians(degrees)
    cos_t = math.cos(radians)
    sin_t = math.sin(radians)
    px, py, pz = (point[i] - origin[i] for i in range(3))
    dot = ux * px + uy * py + uz * pz
    cross = (uy * pz - uz * py, uz * px - ux * pz, ux * py - uy * px)
    return (
        origin[0] + px * cos_t + cross[0] * sin_t + ux * dot * (1 - cos_t),
        origin[1] + py * cos_t + cross[1] * sin_t + uy * dot * (1 - cos_t),
        origin[2] + pz * cos_t + cross[2] * sin_t + uz * dot * (1 - cos_t),
    )


def _unit(vector: Vec3) -> Vec3:
    length = math.sqrt(sum(component * component for component in vector))
    if length == 0:
        return (0.0, 0.0, 0.0)
    return tuple(component / length for component in vector)  # type: ignore[return-value]


def _perpendicular_axis(axis: Vec3) -> Vec3:
    candidate = (0.0, 1.0, 0.0) if abs(axis[1]) < 0.9 else (1.0, 0.0, 0.0)
    return _unit(_cross(axis, candidate))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
