import random

import pytest

from orthoplan.evaluation.rules.contact_geometry import _min_triangle_distance, _triangle_distance
from orthoplan.mesh_intersect import triangles_intersect
from orthoplan.triangle_distance import minimum_triangle_distance


def exhaustive(first, second):
    if any(triangles_intersect(a, b) for a in first for b in second):
        return 0.0
    return min(_triangle_distance(a, b) for a in first for b in second)


def test_hierarchy_matches_exhaustive_narrow_phase():
    rng = random.Random(72)
    for offset in [0, .5, 3]:
        first = [tuple(tuple(rng.random() for _ in range(3)) for _ in range(3)) for _ in range(12)]
        second = [tuple(tuple(rng.random() + offset for _ in range(3)) for _ in range(3)) for _ in range(11)]
        assert _min_triangle_distance(first, second) == pytest.approx(exhaustive(first, second), abs=1e-10)


def test_large_surfaces_prune_pairs_without_sampling():
    first = [((i * 2., 0., 0.), (i * 2. + 1, 0., 0.), (i * 2., 1., 0.)) for i in range(400)]
    second = [tuple((x, y, z + .7) for x, y, z in tri) for tri in first]
    calls = 0

    def distance(a, b):
        nonlocal calls
        calls += 1
        return _triangle_distance(a, b)

    result = minimum_triangle_distance(first, second, intersects=triangles_intersect, distance=distance)
    assert result == pytest.approx(.7)
    assert calls < len(first) * len(second) // 10
