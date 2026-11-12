"""Bounded full-triangle surface separation checks, without optional dependencies."""
import time
from orthoplan.mesh_intersect import triangles_intersect
from orthoplan.triangle_distance import minimum_triangle_distance


class ContactBudgetExceeded(RuntimeError):
    pass


def surface_distance(left, right, *, seconds=5, max_tests=100000):
    from orthoplan.evaluation.rules.contact_geometry import _triangle_distance
    if not len(left) or not len(right):
        return {'status': 'unavailable', 'distance': None, 'reason': 'Missing region surface'}
    started, tests = time.monotonic(), 0

    def bounded(fn):
        def call(a, b):
            nonlocal tests
            tests += 1
            if tests > max_tests or time.monotonic()-started > seconds:
                raise ContactBudgetExceeded()
            return fn(a, b)
        return call

    triangles = [[tuple(map(tuple, t)) for t in mesh] for mesh in (left, right)]
    try:
        distance = minimum_triangle_distance(*triangles, intersects=bounded(triangles_intersect), distance=bounded(_triangle_distance))
        return {'status': 'complete', 'distance': distance, 'surface_contact_or_intersection': distance <= 1e-9,
                'triangle_tests': tests, 'method': 'All triangles, bounding-volume pruning; no sampling'}
    except ContactBudgetExceeded:
        return {'status': 'indeterminate', 'distance': None, 'triangle_tests': tests,
                'reason': 'Computation budget reached; no clearance conclusion'}
