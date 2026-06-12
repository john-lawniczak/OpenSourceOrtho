"""Surface boundary-cost signals for the hybrid segmenter (dependency-free).

The hybrid segmenter scores candidate cut positions along the arch from three
surface signals: occlusal-height valleys, a curvature proxy, and face-normal
changes. This module owns that scoring stack; ``hybrid`` owns cut placement and
segment assembly.
"""

from __future__ import annotations

from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.arch_profile import bucket_of, height_profile


def score_arch_buckets(
    positions: list[float],
    heights: list[float],
    normals: list[Vec3],
    buckets: int,
) -> tuple[list[float], float, float]:
    """Boundary-cost score per arc bucket, plus the (lo, span) bucket mapping."""

    height, lo, span = height_profile(positions, heights, buckets)
    normal_signal = _bucket_average(
        positions,
        [_normal_change(normal) for normal in normals],
        lo,
        span,
        buckets,
    )
    return _boundary_scores(height, normal_signal, _curvature_proxy(height)), lo, span


def _normal_change(normal: Vec3) -> float:
    # Crowns are not vertical cliffs, but interproximal boundaries often produce
    # more abrupt face-normal changes than smooth labial/lingual crown surfaces.
    return 1.0 - abs(normal[2])


def _bucket_average(
    positions: list[float],
    values: list[float],
    lo: float,
    span: float,
    buckets: int,
) -> list[float]:
    sums = [0.0] * buckets
    counts = [0] * buckets
    for position, value in zip(positions, values):
        index = bucket_of(position, lo, span, buckets)
        sums[index] += value
        counts[index] += 1
    out: list[float] = []
    previous = 0.0
    for total, count in zip(sums, counts):
        if count:
            previous = total / count
        out.append(previous)
    return out


def _curvature_proxy(profile: list[float]) -> list[float]:
    if len(profile) < 3:
        return [0.0] * len(profile)
    out = [0.0]
    for index in range(1, len(profile) - 1):
        out.append(abs(profile[index - 1] - 2 * profile[index] + profile[index + 1]))
    out.append(0.0)
    return out


def _normalize(values: list[float], *, invert: bool = False) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo <= 1e-9:
        normalized = [0.0] * len(values)
    else:
        normalized = [(value - lo) / (hi - lo) for value in values]
    if invert:
        return [1.0 - value for value in normalized]
    return normalized


def _boundary_scores(
    height: list[float],
    normal_signal: list[float],
    curvature_signal: list[float],
) -> list[float]:
    valley = _normalize(height, invert=True)
    normals = _normalize(normal_signal)
    curvature = _normalize(curvature_signal)
    return [
        0.58 * valley_value + 0.24 * curvature_value + 0.18 * normal_value
        for valley_value, curvature_value, normal_value in zip(valley, curvature, normals)
    ]
