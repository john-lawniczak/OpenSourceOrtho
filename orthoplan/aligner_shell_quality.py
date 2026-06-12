from __future__ import annotations

import math
from collections.abc import Iterable

from orthoplan.mesh_intersect import triangles_intersect
from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]
Bounds = tuple[Vec3, Vec3]
Cell = tuple[int, int, int]

_EPS = 1e-9


def count_self_intersections(triangles: list[Triangle]) -> int:
    """Real triangle-triangle self-intersection count.

    A uniform spatial grid is the broad phase; only triangles whose boxes land in
    a shared cell are checked for true AABB overlap and then confirmed with the
    exact triangle-triangle test. Only genuine crossings count.
    """

    boxes = [_bounds(tri) for tri in triangles]
    grid = _triangle_grid(boxes)
    checked: set[tuple[int, int]] = set()
    count = 0
    for candidates in grid.values():
        if len(candidates) < 2:
            continue
        for index, other in _candidate_pairs(candidates, checked):
            tri_a = triangles[index]
            tri_b = triangles[other]
            if not _boxes_overlap(boxes[index], boxes[other]):
                continue  # broad phase reject for same-cell edge cases
            if _shares_vertex(tri_a, tri_b):
                continue  # shared vertex/edge: adjacent faces, not a defect
            if triangles_intersect(tri_a, tri_b):
                count += 1
    return count


def _candidate_pairs(
    candidates: list[int], checked: set[tuple[int, int]]
) -> Iterable[tuple[int, int]]:
    for offset, index in enumerate(candidates):
        for other in candidates[offset + 1:]:
            pair = (index, other) if index < other else (other, index)
            if pair in checked:
                continue
            checked.add(pair)
            yield pair


def _shares_vertex(tri_a: Triangle, tri_b: Triangle) -> bool:
    return bool(set(tri_a) & set(tri_b))


def _triangle_grid(boxes: list[Bounds]) -> dict[Cell, list[int]]:
    if not boxes:
        return {}
    cell_size = _triangle_cell_size(boxes)
    grid: dict[Cell, list[int]] = {}
    for index, bounds in enumerate(boxes):
        for cell in _cells_for_bounds(bounds, cell_size):
            grid.setdefault(cell, []).append(index)
    return grid


def _triangle_cell_size(boxes: list[Bounds]) -> float:
    extents = [
        max(hi[axis] - lo[axis] for axis in range(3))
        for lo, hi in boxes
    ]
    useful = sorted(extent for extent in extents if extent > _EPS)
    if useful:
        return useful[len(useful) // 2]
    scene = _scene_bounds_from_boxes(boxes)
    diagonal = math.dist(scene[0], scene[1])
    return max(diagonal, 1.0)


def _cells_for_bounds(bounds: Bounds, cell_size: float) -> Iterable[Cell]:
    lo, hi = bounds
    ranges = [
        range(
            math.floor((lo[axis] - _EPS) / cell_size),
            math.floor((hi[axis] + _EPS) / cell_size) + 1,
        )
        for axis in range(3)
    ]
    for x in ranges[0]:
        for y in ranges[1]:
            for z in ranges[2]:
                yield (x, y, z)


def count_self_intersections_quadratic_reference(triangles: list[Triangle]) -> int:
    """Slow exact reference used by regression tests."""

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
    cell_size = _point_cell_size([*inner, *outer])
    grid = _point_grid(outer, cell_size)
    best = math.inf
    occupied = list(grid)
    for point in inner:
        best = min(best, _nearest_distance(point, grid, occupied, cell_size, best))
    return best if math.isfinite(best) else 0.0


def _quantize(vertex: Vec3) -> tuple[int, int, int]:
    return (round(vertex[0] * 1_000_000), round(vertex[1] * 1_000_000), round(vertex[2] * 1_000_000))


def _point_grid(points: list[Vec3], cell_size: float) -> dict[Cell, list[Vec3]]:
    grid: dict[Cell, list[Vec3]] = {}
    for point in points:
        grid.setdefault(_cell_for_point(point, cell_size), []).append(point)
    return grid


def _point_cell_size(points: list[Vec3]) -> float:
    lo, hi = _scene_bounds_from_points(points)
    diagonal = math.dist(lo, hi)
    if diagonal <= _EPS:
        return 1.0
    return max(diagonal / max(round(len(points) ** (1 / 3)), 1), _EPS)


def _nearest_distance(
    point: Vec3,
    grid: dict[Cell, list[Vec3]],
    occupied: list[Cell],
    cell_size: float,
    best_limit: float,
) -> float:
    best = best_limit
    for cell in occupied:
        if _cell_lower_bound(point, cell, cell_size) > best + _EPS:
            continue
        for candidate in grid[cell]:
            best = min(best, math.dist(point, candidate))
    return best


def _cell_for_point(point: Vec3, cell_size: float) -> Cell:
    return (
        math.floor(point[0] / cell_size),
        math.floor(point[1] / cell_size),
        math.floor(point[2] / cell_size),
    )


def _cell_lower_bound(point: Vec3, cell: Cell, cell_size: float) -> float:
    lower = (
        cell[0] * cell_size,
        cell[1] * cell_size,
        cell[2] * cell_size,
    )
    upper = (
        (cell[0] + 1) * cell_size,
        (cell[1] + 1) * cell_size,
        (cell[2] + 1) * cell_size,
    )
    gaps = [
        max(lower[axis] - point[axis], point[axis] - upper[axis], 0.0)
        for axis in range(3)
    ]
    return math.sqrt(sum(gap * gap for gap in gaps))


def min_inner_outer_clearance_quadratic_reference(inner: list[Vec3], outer: list[Vec3]) -> float:
    """Slow exact reference used by regression tests."""

    if not inner or not outer:
        return 0.0
    return min(math.dist(a, b) for a in inner for b in outer)


def _bounds(tri: Triangle) -> Bounds:
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


def _scene_bounds_from_boxes(boxes: list[Bounds]) -> Bounds:
    return (
        tuple(min(bounds[0][axis] for bounds in boxes) for axis in range(3)),  # type: ignore[return-value]
        tuple(max(bounds[1][axis] for bounds in boxes) for axis in range(3)),  # type: ignore[return-value]
    )


def _scene_bounds_from_points(points: list[Vec3]) -> Bounds:
    return (
        tuple(min(point[axis] for point in points) for axis in range(3)),  # type: ignore[return-value]
        tuple(max(point[axis] for point in points) for axis in range(3)),  # type: ignore[return-value]
    )
