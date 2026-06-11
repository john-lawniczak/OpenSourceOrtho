from __future__ import annotations

import math

from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]


def triangle_aabb_intersection_count(triangles: list[Triangle]) -> int:
    """Approximate self-intersection signal via disjoint triangle AABB overlap."""

    boxes = [_bounds(tri) for tri in triangles]
    count = 0
    for index, tri_a in enumerate(triangles):
        vertices_a = set(tri_a)
        for other in range(index + 1, len(triangles)):
            if vertices_a & set(triangles[other]):
                continue
            if _boxes_overlap(boxes[index], boxes[other]):
                count += 1
    return count


def min_inner_outer_clearance(inner: list[Vec3], outer: list[Vec3]) -> float:
    """Minimum sampled distance between any inner vertex and any outer vertex."""

    if not inner or not outer:
        return 0.0
    return min(math.dist(a, b) for a in inner for b in outer)


def _bounds(tri: Triangle) -> tuple[Vec3, Vec3]:
    return (
        tuple(min(vertex[axis] for vertex in tri) for axis in range(3)),  # type: ignore[return-value]
        tuple(max(vertex[axis] for vertex in tri) for axis in range(3)),  # type: ignore[return-value]
    )


def _boxes_overlap(a: tuple[Vec3, Vec3], b: tuple[Vec3, Vec3]) -> bool:
    return all(
        min(a[1][axis], b[1][axis]) - max(a[0][axis], b[0][axis]) > 1e-9
        for axis in range(3)
    )
