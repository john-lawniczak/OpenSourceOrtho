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
    arc_context,
    arc_position_of,
    bucket_of,
    place_cuts,
)
from orthoplan.segmentation.heuristic import (
    Triangle,
    ToothSegment,
    default_arch_order,
    teeth_from_signal,
)
from orthoplan.segmentation.surface_signals import score_arch_buckets
from orthoplan.segmentation.prior_blend import (
    CrossModalReport,
    blend_prior_scores,
    cross_modal_confidence,
    cross_modal_report,
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
    cross_modal: CrossModalReport | None = None


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
    prior_points: list[Vec3] | None = None,
    prior_boost: bool = False,
) -> list[ToothSegment]:
    """Partition a whole-arch STL into reviewable per-tooth crown proposals."""

    segments, _diagnostics = hybrid_segment_arch_with_diagnostics(
        vertices,
        arch=arch,
        tooth_values=tooth_values,
        prior_points=prior_points,
        prior_boost=prior_boost,
    )
    return segments


def hybrid_segment_arch_with_diagnostics(
    vertices: list[Vec3],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
    prior_points: list[Vec3] | None = None,
    prior_boost: bool = False,
) -> tuple[list[ToothSegment], HybridSegmentationDiagnostics]:
    facets = _facets(vertices)
    if len(facets) < _MIN_TRIANGLES_PER_TOOTH:
        return [], HybridSegmentationDiagnostics(mesh_processing_backend(), (), ())

    centroids = [_tri_centroid(facet) for facet in facets]
    context = arc_context(centroids)
    positions = [arc_position_of(centroid, context) for centroid in centroids]
    heights = [centroid[2] for centroid in centroids]
    normals = [_normal(facet) for facet in facets]

    canonical = len(default_arch_order(arch))
    resolution = len(tooth_values) if tooth_values is not None else canonical
    buckets = resolution * _BUCKETS_PER_TOOTH
    scores, lo, span = score_arch_buckets(positions, heights, normals, buckets)
    prior_buckets = _prior_buckets(prior_points, context, lo, span, buckets)
    if prior_buckets:
        scores = blend_prior_scores(scores, prior_buckets)
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
    penalty = _COUNT_MISMATCH_PENALTY if (tooth_values is None and count != canonical) else 1.0
    cross_modal = cross_modal_report(boundary_buckets, prior_buckets, prior_boost)

    groups: list[list[int]] = [[] for _ in range(count)]
    for index, position in enumerate(positions):
        segment_index = bisect_right(
            boundary_buckets,
            bucket_of(position, lo, span, buckets),
        )
        groups[min(segment_index, count - 1)].append(index)

    segments = _assemble_segments(
        groups, teeth, facets, centroids, boundary_scores, penalty, cross_modal
    )
    return segments, HybridSegmentationDiagnostics(
        backend=mesh_processing_backend(),
        boundary_buckets=tuple(boundary_buckets),
        boundary_scores=tuple(round(score, 6) for score in boundary_scores),
        cross_modal=cross_modal,
    )


def _prior_buckets(prior_points, context, lo, span, buckets) -> list[int]:
    """CBCT boundary priors (scan space) mapped into cut-score buckets.

    Priors travel through the SAME arc context as the scan triangles, so the
    score bias lands exactly where the volume says the embrasure is.
    """

    return sorted(
        bucket_of(arc_position_of(point, context), lo, span, buckets)
        for point in (prior_points or [])
    )


def _assemble_segments(
    groups: list[list[int]],
    teeth: tuple[str, ...],
    facets: list[Triangle],
    centroids: list[Vec3],
    boundary_scores: list[float],
    penalty: float,
    cross_modal: CrossModalReport | None,
) -> list[ToothSegment]:
    """Build the per-tooth segments with (optionally cross-modal) confidence."""

    max_score = max(boundary_scores) if boundary_scores else 0.0
    segments: list[ToothSegment] = []
    for index, indices in enumerate(groups):
        if not indices:
            continue
        confidence = _segment_confidence(index, boundary_scores, max_score) * penalty
        if cross_modal is not None:
            confidence = cross_modal_confidence(confidence, index, cross_modal)
        segments.append(
            ToothSegment(
                tooth_value=teeth[index],
                triangles=[facets[i] for i in indices],
                centroid=_mean3([centroids[i] for i in indices]),
                confidence=round(confidence, 3),
            )
        )
    return segments


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
