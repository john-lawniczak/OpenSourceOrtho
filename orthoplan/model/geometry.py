"""Typed coordinate frames for tooth movement.

Phase 1 replaces the previous free-form ``coordinate_frame`` string with an
explicit, serializable frame definition so that units and axis semantics are
never implicit.

Axis semantics for the canonical authoring frame (``scan-local``):

- ``z`` is the occlusogingival (vertical) axis. Positive ``z`` is occlusal.
  Vertical translation (intrusion/extrusion) is well defined in this frame.
- ``x`` and ``y`` span the horizontal occlusal plane. Their mapping to the
  per-tooth mesiodistal and buccolingual axes is NOT resolved at the global
  scan level, because those axes are tooth-specific.

Consequence: ``tip`` (mesiodistal angulation) and ``torque`` (buccolingual
inclination) and long-axis ``rotation`` cannot be converted into a renderable
transform without a per-tooth local frame. When those axes are unavailable we
mark the conversion as UNAVAILABLE rather than guessing an orientation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Handedness(StrEnum):
    RIGHT = "right-handed"
    LEFT = "left-handed"


class AnatomicalDirection(StrEnum):
    """Anatomical meaning of a frame axis.

    ``UNKNOWN`` means the axis is a scan-space direction whose per-tooth
    anatomical meaning is not resolved (true at the global scan level).
    """

    MESIODISTAL = "mesiodistal"
    BUCCOLINGUAL = "buccolingual"
    OCCLUSOGINGIVAL = "occlusogingival"
    UNKNOWN = "unknown"


class AxisSemantics(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: AnatomicalDirection = AnatomicalDirection.UNKNOWN
    y: AnatomicalDirection = AnatomicalDirection.UNKNOWN
    z: AnatomicalDirection = AnatomicalDirection.OCCLUSOGINGIVAL


class CoordinateFrame(BaseModel):
    """A named, typed coordinate frame.

    A frame is renderable for tip/torque only when the mesiodistal and
    buccolingual axes are both resolved. The canonical Phase 1 scan frame does
    not resolve them, so tip/torque/rotation conversion is unavailable.
    """

    model_config = ConfigDict(frozen=True)

    name: str = "scan-local"
    handedness: Handedness = Handedness.RIGHT
    axes: AxisSemantics = AxisSemantics()
    origin: str = "scan-local origin (not an anatomical landmark)"

    @property
    def vertical_axis_resolved(self) -> bool:
        return AnatomicalDirection.OCCLUSOGINGIVAL in (self.axes.x, self.axes.y, self.axes.z)

    @property
    def tip_torque_convertible(self) -> bool:
        resolved = {self.axes.x, self.axes.y, self.axes.z}
        return (
            AnatomicalDirection.MESIODISTAL in resolved
            and AnatomicalDirection.BUCCOLINGUAL in resolved
        )


# Canonical authoring frame for Phase 1. Vertical (z) is resolved; horizontal
# anatomical axes are not, so tip/torque/rotation are not renderable yet.
SCAN_FRAME = CoordinateFrame()


Vec3 = tuple[float, float, float]

Matrix4 = list[list[float]]


def invert_affine(matrix: Matrix4) -> Matrix4 | None:
    """Invert a ``[R t; 0 1]`` affine: inverse = ``[A^-1, -A^-1 t]``. None if singular.

    Registration matrices map STL (scan) space into CBCT space; CBCT-derived
    anatomy comes back into scan space through this inverse. Pure list math so
    the core stays dependency-free.
    """

    a = [row[:3] for row in matrix[:3]]
    t = [matrix[0][3], matrix[1][3], matrix[2][3]]
    det = (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )
    if abs(det) < 1e-12:
        return None
    cof = [
        [
            (a[1][1] * a[2][2] - a[1][2] * a[2][1]) / det,
            (a[0][2] * a[2][1] - a[0][1] * a[2][2]) / det,
            (a[0][1] * a[1][2] - a[0][2] * a[1][1]) / det,
        ],
        [
            (a[1][2] * a[2][0] - a[1][0] * a[2][2]) / det,
            (a[0][0] * a[2][2] - a[0][2] * a[2][0]) / det,
            (a[0][2] * a[1][0] - a[0][0] * a[1][2]) / det,
        ],
        [
            (a[1][0] * a[2][1] - a[1][1] * a[2][0]) / det,
            (a[0][1] * a[2][0] - a[0][0] * a[2][1]) / det,
            (a[0][0] * a[1][1] - a[0][1] * a[1][0]) / det,
        ],
    ]
    inv_t = [-sum(cof[i][j] * t[j] for j in range(3)) for i in range(3)]
    return [
        [cof[0][0], cof[0][1], cof[0][2], inv_t[0]],
        [cof[1][0], cof[1][1], cof[1][2], inv_t[1]],
        [cof[2][0], cof[2][1], cof[2][2], inv_t[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def apply_affine(matrix: Matrix4, point: Vec3) -> Vec3:
    """Apply a 4x4 affine to a POINT (rotation + translation)."""

    return (
        matrix[0][0] * point[0] + matrix[0][1] * point[1] + matrix[0][2] * point[2] + matrix[0][3],
        matrix[1][0] * point[0] + matrix[1][1] * point[1] + matrix[1][2] * point[2] + matrix[1][3],
        matrix[2][0] * point[0] + matrix[2][1] * point[1] + matrix[2][2] * point[2] + matrix[2][3],
    )


def apply_affine_direction(matrix: Matrix4, direction: Vec3) -> Vec3:
    """Apply only the linear part of a 4x4 affine to a DIRECTION (no translation)."""

    return (
        matrix[0][0] * direction[0] + matrix[0][1] * direction[1] + matrix[0][2] * direction[2],
        matrix[1][0] * direction[0] + matrix[1][1] * direction[1] + matrix[1][2] * direction[2],
        matrix[2][0] * direction[0] + matrix[2][1] * direction[1] + matrix[2][2] * direction[2],
    )

APPROXIMATE_FRAME_NOTE = (
    "Approximate visualization frame from crown-surface PCA. Axes are ordered by "
    "geometric variance, NOT anatomy; this is not a mesiodistal/buccolingual/long-axis "
    "measurement and says nothing about root direction."
)


class ToothLocalFrame(BaseModel):
    """A per-tooth local frame derived from segmented crown geometry.

    Phase 3 derives this from PCA of the crown mesh, so it is explicitly an
    APPROXIMATE metadata/debug aid. ``axes`` are the principal directions ordered
    by descending variance, not resolved anatomical axes. Approximate frames do
    not authorize rendered rotation; a trusted frame must set
    ``approximate=False``.
    """

    model_config = ConfigDict(frozen=True)

    origin: Vec3
    axes: tuple[Vec3, Vec3, Vec3]
    source: str = "pca-crown"
    approximate: bool = True
    note: str = APPROXIMATE_FRAME_NOTE
