"""1D arch-profile helpers for valley-based tooth separation (dependency-free).

The whole-arch scan is reduced to a 1D signal walked along the dental arch: the
occlusal height of the surface as a function of arc position. Crowns are peaks;
the interproximal embrasures between adjacent teeth are valleys. Cutting at those
valleys separates teeth far better than equal-angle slicing.

Everything here is pure list math (no numpy) and deterministic.
"""

from __future__ import annotations

from math import tau

NEG_INF = float("-inf")


def wrap_origin(angles: list[float]) -> float:
    """Angle just after the largest angular gap (the mouth opening).

    Rotating arc positions to start there makes the teeth a single contiguous run
    even when the arch straddles the +/-pi discontinuity.
    """

    ordered = sorted(angles)
    best_gap = (ordered[0] + tau) - ordered[-1]  # wrap-around gap
    origin = ordered[0]
    for previous, current in zip(ordered, ordered[1:]):
        gap = current - previous
        if gap > best_gap:
            best_gap, origin = gap, current
    return origin


def arc_positions(angles: list[float], origin: float) -> list[float]:
    """Angles re-expressed as contiguous arc positions in ``[0, tau)`` from origin."""

    return [(angle - origin) % tau for angle in angles]


def height_profile(
    positions: list[float], heights: list[float], buckets: int
) -> tuple[list[float], float, float]:
    """Max occlusal height per arc bucket, with empty buckets back-filled.

    Returns ``(profile, lo, span)`` so callers can map an arc position to a bucket.
    """

    lo = min(positions)
    span = max(max(positions) - lo, 1e-9)
    profile = [NEG_INF] * buckets
    for position, height in zip(positions, heights):
        index = min(buckets - 1, int((position - lo) / span * buckets))
        if height > profile[index]:
            profile[index] = height
    _backfill(profile)
    return _smooth(profile), lo, span


def bucket_of(position: float, lo: float, span: float, buckets: int) -> int:
    return min(buckets - 1, max(0, int((position - lo) / span * buckets)))


def _backfill(profile: list[float]) -> None:
    last = next((value for value in profile if value != NEG_INF), 0.0)
    for index, value in enumerate(profile):
        if value == NEG_INF:
            profile[index] = last
        else:
            last = value


def _smooth(profile: list[float]) -> list[float]:
    out: list[float] = []
    for index in range(len(profile)):
        lo = max(0, index - 1)
        hi = min(len(profile), index + 2)
        window = profile[lo:hi]
        out.append(sum(window) / len(window))
    return out


def _prominence(profile: list[float], index: int) -> float:
    left_peak = max(profile[: index + 1])
    right_peak = max(profile[index:])
    return min(left_peak, right_peak) - profile[index]


def find_boundaries(profile: list[float], cuts: int) -> list[tuple[int, float]]:
    """Boundary buckets between teeth, as (bucket index, prominence) pairs.

    Each cut starts at its equal-spacing position (so teeth stay balanced and we
    never produce a few huge segments) and is then snapped to the lowest point - a
    real interproximal valley - within half a tooth either side. The valley's
    prominence drives that tooth's confidence: a deep, clean dip scores higher, a
    flat region (no real gap) scores near the floor.
    """

    if cuts <= 0:
        return []
    length = len(profile)
    step = length / (cuts + 1)
    window = max(1, int(step / 2))
    boundaries: list[tuple[int, float]] = []
    previous = 0
    for k in range(1, cuts + 1):
        nominal = round(k * step)
        lo = max(previous + 1, nominal - window)
        hi = min(length - 1, nominal + window)
        index = nominal if lo > hi else min(range(lo, hi + 1), key=lambda b: profile[b])
        index = max(previous + 1, min(index, length - 1))
        boundaries.append((index, _prominence(profile, index)))
        previous = index
    return boundaries
