"""1D arch-profile helpers behind the valley-based segmentation heuristic."""

from __future__ import annotations

from math import tau

from orthoplan.segmentation.arch_profile import (
    arc_positions,
    find_boundaries,
    height_profile,
    wrap_origin,
)


def test_height_profile_backfills_empty_buckets() -> None:
    profile, lo, span = height_profile([0.0, 1.0], [5.0, 7.0], 6)
    assert all(value != float("-inf") for value in profile)
    assert span > 0


def test_find_boundaries_snaps_to_planted_valleys() -> None:
    # A high plateau with two deep dips: cuts must land on the dips, with positive
    # prominence (a real gap), not at arbitrary equal-spacing positions.
    profile = [10.0] * 30
    profile[10] = 1.0
    profile[20] = 1.0
    boundaries = find_boundaries(profile, 2)
    indices = [index for index, _ in boundaries]
    proms = [prominence for _, prominence in boundaries]
    assert any(abs(index - 10) <= 2 for index in indices)
    assert any(abs(index - 20) <= 2 for index in indices)
    assert all(prom > 0 for prom in proms)


def test_find_boundaries_count_is_stable_and_monotonic() -> None:
    # Even on a flat-ish signal the count stays exact and boundaries are distinct
    # and increasing (so no tooth segment collapses to empty).
    profile = [float(i % 2) for i in range(40)]
    boundaries = find_boundaries(profile, 5)
    indices = [index for index, _ in boundaries]
    assert len(indices) == 5
    assert indices == sorted(indices)
    assert len(set(indices)) == 5


def test_wrap_origin_and_arc_positions_make_a_contiguous_run() -> None:
    # Angles that straddle the +/-pi seam should unwrap into a contiguous span far
    # smaller than a full circle.
    angles = [3.0, 3.1, -3.1, -3.0]  # clustered around +/-pi
    positions = arc_positions(angles, wrap_origin(angles))
    assert max(positions) - min(positions) < tau / 2
