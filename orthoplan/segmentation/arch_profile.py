"""1D arch-profile helpers for valley-based tooth separation (dependency-free).

The whole-arch scan is reduced to a 1D signal walked along the dental arch: the
occlusal height of the surface as a function of arc position. Crowns are peaks;
the interproximal embrasures between adjacent teeth are valleys. Cutting at those
valleys separates teeth far better than equal-angle slicing.

Everything here is pure list math (no numpy) and deterministic.
"""

from __future__ import annotations

from math import atan2, tau

Vec3 = tuple[float, float, float]
NEG_INF = float("-inf")


def arc_signal(centroids: list[Vec3]) -> tuple[list[float], list[float]]:
    """Arc positions (around the arch centroid) and occlusal heights for centroids.

    Shared by both segmenters so they walk the dental horseshoe identically: the
    polar angle about the mesh centroid becomes a contiguous arc position, and the
    z coordinate is the occlusal height profiled into valleys between crowns.
    """

    center_x = sum(c[0] for c in centroids) / len(centroids)
    center_y = sum(c[1] for c in centroids) / len(centroids)
    angles = [atan2(c[1] - center_y, c[0] - center_x) for c in centroids]
    return arc_positions(angles, wrap_origin(angles)), [c[2] for c in centroids]


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


def _prominence_peak(profile: list[float], index: int) -> float:
    """Prominence of a PEAK: how far it rises above the higher flanking valley."""

    left_valley = min(profile[: index + 1])
    right_valley = min(profile[index:])
    return profile[index] - max(left_valley, right_valley)


def _significant_extrema(
    profile: list[float], *, find_minima: bool
) -> list[tuple[int, float]]:
    """Interior local extrema as ``(index, prominence)`` pairs.

    Minima locate height valleys (embrasures); maxima locate boundary-score peaks
    in the hybrid segmenter's cost signal. Prominence ranks how real each is.
    """

    out: list[tuple[int, float]] = []
    for index in range(1, len(profile) - 1):
        left, here, right = profile[index - 1], profile[index], profile[index + 1]
        if find_minima:
            if here <= left and here <= right and here < max(left, right):
                out.append((index, _prominence(profile, index)))
        elif here >= left and here >= right and here > min(left, right):
            out.append((index, _prominence_peak(profile, index)))
    return out


def detect_cut_count(
    profile: list[float],
    *,
    max_cuts: int,
    prominence_ratio: float = 0.35,
    find_minima: bool = True,
    min_separation: int = 2,
) -> int:
    """Count the significant inter-tooth boundaries WITHOUT assuming a tooth count.

    Real embrasures are the most prominent extrema in the 1D arch signal. Keeping
    only those at least ``prominence_ratio`` of the strongest one lets a clean arch
    report one boundary per real gap and a shorter or partial arch report fewer -
    instead of always forcing the canonical number of cuts. Returns ``0`` when the
    signal carries no usable extrema, signalling the caller to fall back to its
    canonical count rather than invent a split.
    """

    if max_cuts <= 0 or len(profile) < 3:
        return 0
    extrema = _significant_extrema(profile, find_minima=find_minima)
    if not extrema:
        return 0
    max_prominence = max(prominence for _index, prominence in extrema)
    if max_prominence <= 0:
        return 0
    threshold = prominence_ratio * max_prominence
    ranked = sorted(
        (pair for pair in extrema if pair[1] >= threshold),
        key=lambda pair: pair[1],
        reverse=True,
    )
    selected: list[int] = []
    for index, _prominence_value in ranked:
        if all(abs(index - chosen) >= min_separation for chosen in selected):
            selected.append(index)
        if len(selected) >= max_cuts:
            break
    return len(selected)


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
