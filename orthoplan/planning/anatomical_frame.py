"""Trusted per-tooth anatomical frames from reviewed CBCT axes (Step 3).

The engine refuses to render tip/torque/rotation from PCA crown frames because
variance-ordered axes are not anatomy (see ``ToothLocalFrame.approximate``).
This module supplies the validated frame source that contract reserves: when a
plan carries a TRUSTED (human-reviewed, in-field) CBCT-derived tooth axis
behind a registration whose numeric quality gate is open, the tooth's local
frame is rebuilt as:

- axis 0 (tip rotation axis): the buccolingual direction = long axis x tangent
- axis 1 (torque rotation axis): the mesiodistal arch tangent at the tooth,
  from the neighbouring crown centroids, orthogonalized against the long axis
- axis 2 (rotation axis): the trusted CBCT long axis, mapped into scan space
  through the inverse registration and oriented occlusally (+z)

That ordering matches the renderer's contract (frame.axes[0]/[1]/[2] are the
tip/torque/rotation axes). The frame is marked ``approximate=False`` ONLY when
all of: trusted axis, open registration gate, invertible matrix, and a
computable neighbour tangent. Anything less keeps the PCA frame (or none) and
rotation stays unrenderable - fail-closed, never guessed.
"""

from __future__ import annotations

from orthoplan.model.anatomy import ToothAxis
from orthoplan.model.geometry import (
    ToothLocalFrame,
    Vec3,
    apply_affine_direction,
    invert_affine,
)
from orthoplan.model.registration_gate import gate_registration
from orthoplan.segmentation.heuristic import default_arch_order

ANATOMICAL_FRAME_NOTE = (
    "Anatomical visualization frame: axis 2 is the human-reviewed CBCT-derived "
    "long axis (registered into scan space, oriented occlusally); axis 1 is the "
    "mesiodistal arch tangent from neighbouring crown centroids; axis 0 is "
    "buccolingual (long axis x tangent). Axis signs are visualization "
    "conventions; the frame renders rotation and is not a biomechanical claim."
)
# Long axis and arch tangent must not be near-parallel; below this |cross| the
# orthogonalization is numerically meaningless and the frame is not built.
_MIN_AXIS_SEPARATION = 1e-6


def trusted_axis_frames(plan) -> dict[str, ToothLocalFrame]:
    """Non-approximate per-tooth frames for every tooth that has earned one."""

    anatomy = getattr(plan, "derived_anatomy", None)
    if anatomy is None:
        return {}
    inverses = _open_gate_inverses(plan)
    origins = _crown_origins(plan)
    frames: dict[str, ToothLocalFrame] = {}
    for axis in anatomy.tooth_axes:
        tooth = axis.tooth.value
        if not axis.trusted or tooth not in origins:
            continue
        inverse = inverses.get(axis.registration_id)
        if inverse is None:
            continue
        long_axis = _scan_space_long_axis(axis, inverse)
        tangent = _arch_tangent(tooth, origins)
        if long_axis is None or tangent is None:
            continue
        frame = _orthonormal_frame(origins[tooth], long_axis, tangent)
        if frame is not None:
            frames[tooth] = frame
    return frames


def upgrade_tooth_mesh_frames(plan):
    """Plan copy whose tooth meshes carry trusted anatomical frames where earned.

    Only links with no frame or an approximate (PCA) frame are upgraded; an
    explicitly supplied non-approximate frame is never overwritten.
    """

    frames = trusted_axis_frames(plan)
    if not frames:
        return plan
    links = []
    changed = False
    for link in plan.tooth_meshes:
        frame = frames.get(link.tooth.value)
        if frame is not None and (link.local_frame is None or link.local_frame.approximate):
            links.append(link.model_copy(update={"local_frame": frame}))
            changed = True
        else:
            links.append(link)
    if not changed:
        return plan
    return plan.model_copy(update={"tooth_meshes": links})


def _open_gate_inverses(plan) -> dict[str, list[list[float]]]:
    """Inverse (CBCT -> scan) matrices for registrations whose gate is open."""

    out: dict[str, list[list[float]]] = {}
    for registration in getattr(plan, "registrations", None) or []:
        if not gate_registration(registration).open:
            continue
        inverse = invert_affine(registration.matrix)
        if inverse is not None:
            out[registration.id] = inverse
    return out


def _crown_origins(plan) -> dict[str, Vec3]:
    """Crown centroid per segmented tooth (PCA frame origin, or sample mean)."""

    origins: dict[str, Vec3] = {}
    for link in plan.tooth_meshes:
        if link.local_frame is not None:
            origins[link.tooth.value] = link.local_frame.origin
        elif link.surface_sample_points:
            points = link.surface_sample_points
            origins[link.tooth.value] = (
                sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points),
                sum(p[2] for p in points) / len(points),
            )
    return origins


def _scan_space_long_axis(axis: ToothAxis, inverse: list[list[float]]) -> Vec3 | None:
    """The trusted long axis in scan space, unit length, oriented occlusally (+z)."""

    direction = _normalize(apply_affine_direction(inverse, axis.direction))
    if direction is None:
        return None
    # scan-local +z is occlusal by contract (model.geometry); a centerline can be
    # traced root-first or crown-first, so fix the sign deterministically.
    if direction[2] < 0:
        return (-direction[0], -direction[1], -direction[2])
    return direction


def _arch_tangent(tooth: str, origins: dict[str, Vec3]) -> Vec3 | None:
    """Mesiodistal direction at ``tooth``: the arch walked through its neighbours.

    Uses the nearest present neighbour on each side in canonical FDI arch order;
    at an arch end (or with gaps) one side suffices. Returns ``None`` when the
    tooth has no present neighbour - a tangent cannot be guessed.
    """

    order = _arch_order_of(tooth)
    if order is None:
        return None
    index = order.index(tooth)
    previous = next(
        (origins[t] for t in reversed(order[:index]) if t in origins), None
    )
    following = next((origins[t] for t in order[index + 1 :] if t in origins), None)
    if previous is None and following is None:
        return None
    start = previous if previous is not None else origins[tooth]
    end = following if following is not None else origins[tooth]
    return _normalize((end[0] - start[0], end[1] - start[1], end[2] - start[2]))


def _arch_order_of(tooth: str) -> list[str] | None:
    for arch in ("maxillary", "mandibular"):
        order = list(default_arch_order(arch))
        if tooth in order:
            return order
    return None


def _orthonormal_frame(origin: Vec3, long_axis: Vec3, tangent: Vec3) -> ToothLocalFrame | None:
    buccolingual = _normalize(_cross(long_axis, tangent))
    if buccolingual is None:
        return None
    mesiodistal = _cross(buccolingual, long_axis)  # unit: cross of orthonormal units
    return ToothLocalFrame(
        origin=origin,
        axes=(buccolingual, mesiodistal, long_axis),
        source="cbct-axis+arch-tangent",
        approximate=False,
        note=ANATOMICAL_FRAME_NOTE,
    )


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(vector: Vec3) -> Vec3 | None:
    length = (vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2) ** 0.5
    if length < _MIN_AXIS_SEPARATION:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)
