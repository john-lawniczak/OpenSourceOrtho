from __future__ import annotations

import math

from orthoplan.mesh_intersect import triangles_intersect
from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]


def count_self_intersections(triangles: list[Triangle]) -> int:
    """Real triangle-triangle self-intersection count.

    AABB overlap is kept as a cheap broad phase; every box-overlapping pair that
    does not share a vertex (adjacency in a closed mesh is not a defect) is then
    confirmed with an exact triangle-triangle test. Only genuine crossings count.
    """

    boxes = [_bounds(tri) for tri in triangles]
    count = 0
    for index, tri_a in enumerate(triangles):
        vertices_a = set(tri_a)
        for other in range(index + 1, len(triangles)):
            if vertices_a & set(triangles[other]):
                continue  # shared vertex/edge: adjacent faces, not a defect
            if not _boxes_overlap(boxes[index], boxes[other]):
                continue  # broad phase reject
            if triangles_intersect(tri_a, triangles[other]):
                count += 1
    return count


def count_nonmanifold_edges(triangles: list[Triangle]) -> int:
    """Edges shared by more than two faces - a nonmanifold defect."""

    counts: dict[tuple[tuple[int, ...], tuple[int, ...]], int] = {}
    for tri in triangles:
        keys = [_quantize(vertex) for vertex in tri]
        for i in range(3):
            edge = (keys[i], keys[(i + 1) % 3])
            ordered = (min(edge), max(edge))
            counts[ordered] = counts.get(ordered, 0) + 1
    return sum(1 for total in counts.values() if total > 2)


def min_inner_outer_clearance(inner: list[Vec3], outer: list[Vec3]) -> float:
    """Minimum sampled distance between any inner vertex and any outer vertex."""

    if not inner or not outer:
        return 0.0
    return min(math.dist(a, b) for a in inner for b in outer)


def _quantize(vertex: Vec3) -> tuple[int, int, int]:
    return (round(vertex[0] * 1_000_000), round(vertex[1] * 1_000_000), round(vertex[2] * 1_000_000))


def _bounds(tri: Triangle) -> tuple[Vec3, Vec3]:
    return (
        tuple(min(vertex[axis] for vertex in tri) for axis in range(3)),  # type: ignore[return-value]
        tuple(max(vertex[axis] for vertex in tri) for axis in range(3)),  # type: ignore[return-value]
    )


def _boxes_overlap(a: tuple[Vec3, Vec3], b: tuple[Vec3, Vec3]) -> bool:
    # Inclusive (touching boxes count): a real triangle-triangle crossing can lie
    # exactly on a shared boundary plane, and a triangle that lies in a coordinate
    # plane has zero extent on that axis. The exact narrow-phase test decides; this
    # broad phase must not pre-reject those cases.
    return all(
        min(a[1][axis], b[1][axis]) - max(a[0][axis], b[0][axis]) >= -1e-9
        for axis in range(3)
    )
