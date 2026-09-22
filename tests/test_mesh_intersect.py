from __future__ import annotations

import pytest

from orthoplan.aligner_shell_quality import (
    count_nonmanifold_edges,
    count_self_intersections,
    count_self_intersections_quadratic_reference,
    min_inner_outer_clearance,
    min_inner_outer_clearance_quadratic_reference,
)
from orthoplan.mesh_intersect import triangles_intersect

# A large reference triangle in the z=0 plane, reused across cases.
_FLAT = ((0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (0.0, 4.0, 0.0))


def test_piercing_triangles_intersect() -> None:
    # A vertical triangle whose crossing of the z=0 plane lands inside _FLAT.
    piercing = ((1.0, 1.0, -1.0), (1.0, 1.0, 1.0), (3.0, 1.0, 0.0))
    assert triangles_intersect(_FLAT, piercing) is True


def test_separated_triangles_do_not_intersect() -> None:
    far = ((0.0, 0.0, 5.0), (4.0, 0.0, 5.0), (0.0, 4.0, 5.0))
    assert triangles_intersect(_FLAT, far) is False


def test_parallel_offset_triangles_do_not_intersect() -> None:
    # Same orientation, lifted by 1mm: every vertex is on one side of the plane.
    parallel = ((0.0, 0.0, 1.0), (4.0, 0.0, 1.0), (0.0, 4.0, 1.0))
    assert triangles_intersect(_FLAT, parallel) is False


def test_coplanar_overlapping_triangles_intersect() -> None:
    overlap = ((1.0, 1.0, 0.0), (5.0, 1.0, 0.0), (1.0, 5.0, 0.0))
    assert triangles_intersect(_FLAT, overlap) is True


def test_coplanar_disjoint_triangles_do_not_intersect() -> None:
    disjoint = ((10.0, 10.0, 0.0), (12.0, 10.0, 0.0), (10.0, 12.0, 0.0))
    assert triangles_intersect(_FLAT, disjoint) is False


def test_count_self_intersections_finds_a_real_crossing() -> None:
    piercing = ((1.0, 1.0, -1.0), (1.0, 1.0, 1.0), (3.0, 1.0, 0.0))
    assert count_self_intersections([_FLAT, piercing]) == 1


def test_count_self_intersections_ignores_box_overlap_without_crossing() -> None:
    # Boxes overlap and the triangle pierces the z=0 plane (the old AABB signal
    # would have counted this), but it crosses outside _FLAT's footprint
    # (x+y > 4), so the real engine must report zero.
    outside_pierce = ((3.0, 3.0, -1.0), (3.9, 3.0, -1.0), (3.0, 3.9, 1.0))
    assert _boxes_touch(_FLAT, outside_pierce)
    assert count_self_intersections([_FLAT, outside_pierce]) == 0


def test_grid_self_intersection_matches_quadratic_reference() -> None:
    triangles = [
        _FLAT,
        ((1.0, 1.0, -1.0), (1.0, 1.0, 1.0), (3.0, 1.0, 0.0)),
        ((8.0, 8.0, 0.0), (9.0, 8.0, 0.0), (8.0, 9.0, 0.0)),
        ((3.0, 3.0, -1.0), (3.9, 3.0, -1.0), (3.0, 3.9, 1.0)),
    ]

    assert count_self_intersections(triangles) == count_self_intersections_quadratic_reference(
        triangles
    )


def test_grid_clearance_matches_quadratic_reference() -> None:
    inner = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 8.0, 0.0)]
    outer = [(0.0, 0.0, 0.5), (9.0, 0.0, 0.0), (100.0, 100.0, 100.0)]

    assert min_inner_outer_clearance(inner, outer) == pytest.approx(
        min_inner_outer_clearance_quadratic_reference(inner, outer), abs=1e-9
    )


def test_count_nonmanifold_edges_flags_an_edge_shared_by_three_faces() -> None:
    shared = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    fan = [
        (shared[0], shared[1], (0.0, 1.0, 0.0)),
        (shared[0], shared[1], (0.0, -1.0, 0.0)),
        (shared[0], shared[1], (0.0, 0.0, 1.0)),
    ]
    assert count_nonmanifold_edges(fan) == 1


def test_count_nonmanifold_edges_is_zero_for_manifold_mesh() -> None:
    quad = [
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)),
        ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
    ]
    assert count_nonmanifold_edges(quad) == 0


def _boxes_touch(t1, t2) -> bool:
    for axis in range(3):
        lo = max(min(v[axis] for v in t1), min(v[axis] for v in t2))
        hi = min(max(v[axis] for v in t1), max(v[axis] for v in t2))
        if hi < lo:
            return False
    return True
