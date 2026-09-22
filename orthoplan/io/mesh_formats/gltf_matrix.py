"""Column-major 4x4 helpers for glTF node transforms.

glTF places geometry in node space; a scanner that exports a rotated or scaled
node would otherwise come in mis-oriented. Kept separate from the reader so the
arithmetic is testable on its own.
"""

from __future__ import annotations

Matrix = tuple[float, ...]  # 16 values, column-major, as glTF stores them.

IDENTITY: Matrix = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)


def multiply(left: Matrix, right: Matrix) -> Matrix:
    """``left`` applied after ``right`` (parent x child), column-major."""

    out = [0.0] * 16
    for column in range(4):
        for row in range(4):
            out[column * 4 + row] = sum(
                left[step * 4 + row] * right[column * 4 + step] for step in range(4)
            )
    return tuple(out)


def apply(matrix: Matrix, point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    )


def from_node(node: dict) -> Matrix:
    """A node's local transform: an explicit matrix, or its TRS components."""

    raw = node.get("matrix")
    if isinstance(raw, list) and len(raw) == 16:
        return tuple(float(value) for value in raw)

    translation = _vec(node.get("translation"), (0.0, 0.0, 0.0))
    rotation = _vec(node.get("rotation"), (0.0, 0.0, 0.0, 1.0), length=4)
    scale = _vec(node.get("scale"), (1.0, 1.0, 1.0))
    return multiply(_translate(translation), multiply(_rotate(rotation), _scale(scale)))


def _vec(raw: object, default: tuple[float, ...], *, length: int = 3) -> tuple[float, ...]:
    if isinstance(raw, list) and len(raw) == length:
        try:
            return tuple(float(value) for value in raw)
        except (TypeError, ValueError):
            return default
    return default


def _translate(vector: tuple[float, ...]) -> Matrix:
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        vector[0], vector[1], vector[2], 1.0,
    )


def _scale(vector: tuple[float, ...]) -> Matrix:
    return (
        vector[0], 0.0, 0.0, 0.0,
        0.0, vector[1], 0.0, 0.0,
        0.0, 0.0, vector[2], 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def _rotate(quaternion: tuple[float, ...]) -> Matrix:
    x, y, z, w = quaternion
    return (
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0.0,
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0.0,
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
