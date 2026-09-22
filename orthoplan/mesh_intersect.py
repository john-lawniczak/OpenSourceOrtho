"""Deterministic triangle-triangle intersection (Möller, 1997).

The narrow-phase geometry test behind shell self-intersection QA. It replaces a
bounding-box overlap approximation with a real triangle-triangle overlap test:
the previous signal counted any two triangles whose axis-aligned boxes touched,
which both over-counted (boxes overlap where triangles do not) and under-proved
(box overlap is not intersection). This module answers the actual question -
"do these two triangles share a point in space?" - and stays pure-Python and
dependency-free so it always runs.

Reference: Tomas Möller, "A Fast Triangle-Triangle Intersection Test" (1997).
"""

from __future__ import annotations

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]

_EPS = 1e-9


def triangles_intersect(t1: Triangle, t2: Triangle) -> bool:
    """True if the two triangles share at least one point in 3D space.

    Edge/vertex-adjacent triangles (which legitimately touch in a closed mesh)
    are the caller's responsibility to exclude; this is a pure geometric test.
    """

    v0, v1, v2 = t1
    u0, u1, u2 = t2
    n2 = _cross(_sub(u1, u0), _sub(u2, u0))
    dv = _signed_distances(n2, -_dot(n2, u0), (v0, v1, v2))
    if dv[0] * dv[1] > 0.0 and dv[0] * dv[2] > 0.0:
        return False  # t1 lies entirely on one side of t2's plane
    n1 = _cross(_sub(v1, v0), _sub(v2, v0))
    du = _signed_distances(n1, -_dot(n1, v0), (u0, u1, u2))
    if du[0] * du[1] > 0.0 and du[0] * du[2] > 0.0:
        return False  # t2 lies entirely on one side of t1's plane
    direction = _cross(n1, n2)
    axis = max(range(3), key=lambda i: abs(direction[i]))
    if abs(direction[axis]) < _EPS:
        return _coplanar_intersect(n1, t1, t2)
    interval1 = _interval([v0[axis], v1[axis], v2[axis]], dv)
    interval2 = _interval([u0[axis], u1[axis], u2[axis]], du)
    if interval1 is None or interval2 is None:
        return False
    lo1, hi1 = interval1
    lo2, hi2 = interval2
    return min(hi1, hi2) >= max(lo1, lo2) - _EPS


def _signed_distances(normal: Vec3, offset: float, points) -> list[float]:
    distances = [_dot(normal, p) + offset for p in points]
    return [0.0 if abs(d) < _EPS else d for d in distances]


def _interval(proj: list[float], dist: list[float]) -> tuple[float, float] | None:
    """Parametric span where a triangle crosses the planes' intersection line."""

    if dist[0] * dist[1] > 0.0:
        return _edge_span(proj[2], proj[0], proj[1], dist[2], dist[0], dist[1])
    if dist[0] * dist[2] > 0.0:
        return _edge_span(proj[1], proj[0], proj[2], dist[1], dist[0], dist[2])
    if dist[1] * dist[2] > 0.0 or dist[0] != 0.0:
        return _edge_span(proj[0], proj[1], proj[2], dist[0], dist[1], dist[2])
    if dist[1] != 0.0:
        return _edge_span(proj[1], proj[0], proj[2], dist[1], dist[0], dist[2])
    if dist[2] != 0.0:
        return _edge_span(proj[2], proj[0], proj[1], dist[2], dist[0], dist[1])
    return None  # coplanar; handled by the caller


def _edge_span(p_odd, p_a, p_b, d_odd, d_a, d_b) -> tuple[float, float]:
    t_a = p_odd + (p_a - p_odd) * d_odd / (d_odd - d_a)
    t_b = p_odd + (p_b - p_odd) * d_odd / (d_odd - d_b)
    return (min(t_a, t_b), max(t_a, t_b))


def _coplanar_intersect(normal: Vec3, t1: Triangle, t2: Triangle) -> bool:
    """2D overlap test for triangles that share a plane."""

    abs_n = (abs(normal[0]), abs(normal[1]), abs(normal[2]))
    if abs_n[0] >= abs_n[1] and abs_n[0] >= abs_n[2]:
        i0, i1 = 1, 2
    elif abs_n[1] >= abs_n[2]:
        i0, i1 = 0, 2
    else:
        i0, i1 = 0, 1
    p1 = [(v[i0], v[i1]) for v in t1]
    p2 = [(v[i0], v[i1]) for v in t2]
    for i in range(3):
        for j in range(3):
            if _segments_cross(p1[i], p1[(i + 1) % 3], p2[j], p2[(j + 1) % 3]):
                return True
    return _point_in_triangle(p1[0], p2) or _point_in_triangle(p2[0], p1)


def _segments_cross(a, b, c, d) -> bool:
    d1 = _orient(c, d, a)
    d2 = _orient(c, d, b)
    d3 = _orient(a, b, c)
    d4 = _orient(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_triangle(point, tri) -> bool:
    d1 = _orient(tri[0], tri[1], point)
    d2 = _orient(tri[1], tri[2], point)
    d3 = _orient(tri[2], tri[0], point)
    has_neg = d1 < -_EPS or d2 < -_EPS or d3 < -_EPS
    has_pos = d1 > _EPS or d2 > _EPS or d3 > _EPS
    return not (has_neg and has_pos)


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
