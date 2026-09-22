"""1D arch-profile helpers behind the valley-based segmentation heuristic."""

from __future__ import annotations

from math import tau

from orthoplan.segmentation.arch_profile import (
    arc_positions,
    find_boundaries,
    height_profile,
    place_cuts,
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


def test_place_cuts_picks_deepest_valleys_at_uneven_spacing() -> None:
    # Three valleys of differing depth at NON-uniform spacing. With 2 cuts, the two
    # deepest must be chosen (the shallow one ignored), regardless of even spacing.
    profile = [10.0] * 40
    profile[5] = 0.0    # deepest
    profile[12] = 2.0   # shallow - should be skipped
    profile[30] = 0.5   # second deepest
    indices = place_cuts(profile, 2, find_minima=True, min_separation=3)
    assert indices == [5, 30]


def test_place_cuts_enforces_minimum_separation_no_slivers() -> None:
    # Two valleys only one bucket apart must not BOTH be chosen with a separation
    # of 3 - that was the sliver/label-shift bug. The second cut lands elsewhere.
    profile = [10.0] * 40
    profile[20] = 0.0
    profile[21] = 0.0
    profile[33] = 1.0
    indices = place_cuts(profile, 2, find_minima=True, min_separation=3)
    assert len(indices) == 2
    assert indices == sorted(indices)
    assert all(abs(a - b) >= 3 for a in indices for b in indices if a != b)


def test_place_cuts_peaks_mode_selects_maxima() -> None:
    # find_minima=False is the hybrid segmenter's path: cuts land on score PEAKS.
    profile = [1.0] * 30
    profile[8] = 9.0
    profile[22] = 8.0
    indices = place_cuts(profile, 2, find_minima=False, min_separation=3)
    assert indices == [8, 22]


def test_place_cuts_falls_back_to_distinct_sorted_indices() -> None:
    # A flat signal has no extrema; the fallback must still return exactly `cuts`
    # distinct, sorted, interior boundaries so no tooth region collapses.
    indices = place_cuts([5.0] * 30, 4, find_minima=True, min_separation=3)
    assert len(indices) == 4
    assert len(set(indices)) == 4
    assert indices == sorted(indices)
    assert all(0 < i < 29 for i in indices)


def test_wrap_origin_and_arc_positions_make_a_contiguous_run() -> None:
    # Angles that straddle the +/-pi seam should unwrap into a contiguous span far
    # smaller than a full circle.
    angles = [3.0, 3.1, -3.1, -3.0]  # clustered around +/-pi
    positions = arc_positions(angles, wrap_origin(angles))
    assert max(positions) - min(positions) < tau / 2
