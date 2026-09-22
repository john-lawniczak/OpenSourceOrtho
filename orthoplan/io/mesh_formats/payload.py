"""Format-neutral parse result shared by every scan reader.

A reader's only job is to turn bytes into this payload: de-duplicated points,
triangle indices (empty for a point cloud), a format label, and whatever the
file *declared* about itself. Readers never decide clinical meaning, never
infer units, and never touch the plan contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Vec3 = tuple[float, float, float]
Face = tuple[int, int, int]

# A dental arch scan is large but bounded. These caps stop a malformed or
# hostile file from turning intake into an out-of-memory event.
MAX_POINTS = 8_000_000
MAX_FACES = 8_000_000


@dataclass(frozen=True)
class MeshPayload:
    """Geometry extracted from one scan file.

    ``points`` are the file's vertices in file order. ``faces`` are triangle
    index triples into ``points``; an empty ``faces`` list means the file is a
    point cloud (Revo Scan, for example, exports point-cloud models as PLY,
    OBJ, or ASC with no faces at all).
    """

    points: list[Vec3]
    faces: list[Face]
    source_format: str
    declared_units: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "mesh" if self.faces else "points"

    @property
    def face_count(self) -> int:
        return len(self.faces)

    def triangles(self) -> list[tuple[Vec3, Vec3, Vec3]]:
        """Face indices resolved to coordinate triples."""

        return [
            (self.points[a], self.points[b], self.points[c])
            for a, b, c in self.faces
        ]

    def triangle_soup(self) -> list[Vec3]:
        """Vertices flattened three-per-triangle, or the raw points if faceless.

        Callers that treat the result as a point set (segmentation, bite
        registration) work with either shape; callers that need triangles must
        check :attr:`kind` first.
        """

        if not self.faces:
            return list(self.points)
        return [vertex for triangle in self.triangles() for vertex in triangle]


class MeshParseError(ValueError):
    """Raised when a scan file cannot be read as geometry."""


def validated(payload: MeshPayload) -> MeshPayload:
    """Reject geometry that is empty, out of range, or not finite."""

    if not payload.points:
        raise MeshParseError(f"{payload.source_format} file contains no vertices")
    if len(payload.points) > MAX_POINTS:
        raise MeshParseError(
            f"{payload.source_format} file has {len(payload.points)} vertices, "
            f"above the {MAX_POINTS} supported for one scan"
        )
    if len(payload.faces) > MAX_FACES:
        raise MeshParseError(
            f"{payload.source_format} file has {len(payload.faces)} faces, "
            f"above the {MAX_FACES} supported for one scan"
        )
    if not all(math.isfinite(value) for point in payload.points for value in point):
        raise MeshParseError(f"{payload.source_format} vertex coordinates must be finite")
    limit = len(payload.points)
    for face in payload.faces:
        if any(index < 0 or index >= limit for index in face):
            raise MeshParseError(
                f"{payload.source_format} face references a vertex outside the vertex list"
            )
    return payload


def triangulate(indices: list[int]) -> list[Face]:
    """Fan-triangulate one polygon's vertex indices.

    Quads and n-gons are common in OBJ, PLY, glTF-adjacent, and FBX exports;
    the rest of the engine only handles triangles.
    """

    if len(indices) < 3:
        return []
    return [
        (indices[0], indices[position], indices[position + 1])
        for position in range(1, len(indices) - 1)
    ]
