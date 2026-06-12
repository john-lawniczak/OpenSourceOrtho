"""Hybrid whole-arch STL tooth segmentation.

This module improves the dependency-free valley segmenter by combining three
signals that are available from a surface STL alone:

- arch position along the dental horseshoe
- occlusal-height valleys between crowns
- local surface-shape cues from face normals and a curvature proxy

The final split is still a reviewable draft. The "graph cut" here is a
deterministic mesh-face partition: candidate boundary costs are scored from the
signals above, then triangles are assigned into tooth regions along the arch.
When Open3D is installed, this module records that the optional mesh-processing
backend is available; the pure-Python path remains the tested baseline so the
core app stays lightweight.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.arch_profile import (
    arc_signal,
    bucket_of,
    height_profile,
    place_cuts,
)
from orthoplan.segmentation.heuristic import (
    Triangle,
    ToothSegment,
    default_arch_order,
    teeth_from_signal,
)

_MIN_TRIANGLES_PER_TOOTH = 4
_BUCKETS_PER_TOOTH = 8
_MAX_CONFIDENCE = 0.86
_MIN_CONFIDENCE = 0.22
# Confidence multiplier when the detected count differs from the canonical arch
# (FDI labels become a positional guess; the user must review the numbers).
_COUNT_MISMATCH_PENALTY = 0.6


@dataclass(frozen=True)
class HybridSegmentationDiagnostics:
    """Useful for tests and future UI/debug surfaces."""

    backend: str
    boundary_buckets: tuple[int, ...]
    boundary_scores: tuple[float, ...]


def mesh_processing_backend() -> str:
    """Return the active optional mesh backend name.

    Open3D is optional. Importing it here, instead of at module import time,
    keeps the default install path dependency-free.
    """

    try:
        import open3d  # noqa: F401
    except ImportError:
        return "pure-python"
    return "open3d+pure-python"


def hybrid_segment_arch(
    vertices: list[Vec3],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
) -> list[ToothSegment]:
    """Partition a whole-arch STL into reviewable per-tooth crown proposals."""

    segments, _diagnostics = hybrid_segment_arch_with_diagnostics(
        vertices,
        arch=arch,
        tooth_values=tooth_values,
    )
    return segments


def hybrid_segment_arch_with_diagnostics(
    vertices: list[Vec3],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
) -> tuple[list[ToothSegment], HybridSegmentationDiagnostics]:
    facets = _facets(vertices)
    if len(facets) < _MIN_TRIANGLES_PER_TOOTH:
        return [], HybridSegmentationDiagnostics(mesh_processing_backend(), (), ())

    centroids = [_tri_centroid(facet) for facet in facets]
    positions, heights = arc_signal(centroids)
    normals = [_normal(facet) for facet in facets]

    canonical = len(default_arch_order(arch))
    resolution = len(tooth_values) if tooth_values is not None else canonical
    buckets = resolution * _BUCKETS_PER_TOOTH
    scores, lo, span = _score_arch_buckets(positions, heights, normals, buckets)
    if tooth_values is not None:
        teeth = tooth_values
    else:
        # Count crowns from the height signal (its own fine profile); the cost
        # signal scored above still PLACES the cuts at `buckets` resolution.
        teeth = teeth_from_signal(arch, positions, heights)
    count = len(teeth)
    if len(facets) < count * _MIN_TRIANGLES_PER_TOOTH:
        return [], HybridSegmentationDiagnostics(mesh_processing_backend(), (), ())

    boundaries = _find_graph_cut_boundaries(scores, count - 1)
    boundary_buckets = [bucket for bucket, _score in boundaries]
    boundary_scores = [score for _bucket, score in boundaries]
    max_score = max(boundary_scores) if boundary_scores else 0.0
    penalty = _COUNT_MISMATCH_PENALTY if (tooth_values is None and count != canonical) else 1.0

    groups: list[list[int]] = [[] for _ in range(count)]
    for index, position in enumerate(positions):
        segment_index = bisect_right(
            boundary_buckets,
            bucket_of(position, lo, span, buckets),
        )
        groups[min(segment_index, count - 1)].append(index)

    segments: list[ToothSegment] = []
    for index, indices in enumerate(groups):
        if not indices:
            continue
        segments.append(
            ToothSegment(
                tooth_value=teeth[index],
                triangles=[facets[i] for i in indices],
                centroid=_mean3([centroids[i] for i in indices]),
                confidence=round(_segment_confidence(index, boundary_scores, max_score) * penalty, 3),
            )
        )
    return segments, HybridSegmentationDiagnostics(
        backend=mesh_processing_backend(),
        boundary_buckets=tuple(boundary_buckets),
        boundary_scores=tuple(round(score, 6) for score in boundary_scores),
    )


def _score_arch_buckets(
    positions: list[float],
    heights: list[float],
    normals: list[Vec3],
    buckets: int,
) -> tuple[list[float], float, float]:
    height, lo, span = height_profile(positions, heights, buckets)
    normal_signal = _bucket_average(
        positions,
        [_normal_change(normal) for normal in normals],
        lo,
        span,
        buckets,
    )
    return _boundary_scores(height, normal_signal, _curvature_proxy(height)), lo, span


def _facets(vertices: list[Vec3]) -> list[Triangle]:
    return [
        (vertices[i], vertices[i + 1], vertices[i + 2])
        for i in range(0, len(vertices) - 2, 3)
    ]


def _tri_centroid(tri: Triangle) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


def _mean3(points: list[Vec3]) -> Vec3:
    count = len(points)
    return (
        sum(p[0] for p in points) / count,
        sum(p[1] for p in points) / count,
        sum(p[2] for p in points) / count,
    )


def _normal(tri: Triangle) -> Vec3:
    ax, ay, az = (tri[1][i] - tri[0][i] for i in range(3))
    bx, by, bz = (tri[2][i] - tri[0][i] for i in range(3))
    nx, ny, nz = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


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


def _find_graph_cut_boundaries(scores: list[float], cuts: int) -> list[tuple[int, float]]:
    """Pick the strongest boundary-score buckets along the arch.

    This is the 1D front-end to the mesh-face graph partition: candidate cut costs
    come from surface signals (valley depth, curvature, normal change), and the
    cuts are placed at the most prominent score PEAKS subject to a minimum
    separation (see ``place_cuts``). Unlike the old equal-spacing windows, a cut
    can land where the real embrasure is on an uneven arch, and two cuts never
    collide onto one fissure and steal a tooth into a sliver region.
    """

    if cuts <= 0:
        return []
    step = len(scores) / (cuts + 1)
    min_separation = max(2, round(step / 2))
    indices = place_cuts(scores, cuts, find_minima=False, min_separation=min_separation)
    return [(index, scores[index]) for index in indices]


def _segment_confidence(index: int, boundary_scores: list[float], max_score: float) -> float:
    if max_score <= 0:
        return _MIN_CONFIDENCE
    left = boundary_scores[index - 1] if index > 0 else max_score
    right = boundary_scores[index] if index < len(boundary_scores) else max_score
    ratio = min(left, right) / max_score
    value = _MIN_CONFIDENCE + (_MAX_CONFIDENCE - _MIN_CONFIDENCE) * ratio
    return round(min(_MAX_CONFIDENCE, max(_MIN_CONFIDENCE, value)), 3)
