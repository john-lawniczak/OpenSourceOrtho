"""Heuristic whole-arch tooth segmentation (dependency-free, deterministic).

This is NOT machine learning and NOT clinical. It partitions a whole-arch scan
into per-tooth regions by walking the dental arch in the occlusal plane (z is the
occlusogingival axis, see model.geometry) and cutting at the VALLEYS between
crowns: the surface height dips at the interproximal embrasure between adjacent
teeth, so those dips are the natural tooth boundaries (far better than slicing the
arch into equal-angle sectors). Cuts are labelled in anatomical FDI order.

The output is an APPROXIMATE proposal that must be reviewed and corrected by a
human. Per-tooth ``confidence`` reflects only how cleanly a region separated from
its neighbours (valley prominence) - never clinical certainty, tooth identity, or
treatment validity.

A real on-device learned model (e.g. a Teeth3DS / MeshSegNet network) can replace
this behind the same :class:`ToothSegment` contract; see ``segmentation/auto.py``.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import atan2

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.arch_profile import (
    arc_positions,
    bucket_of,
    find_boundaries,
    height_profile,
    wrap_origin,
)

Triangle = tuple[Vec3, Vec3, Vec3]

# Anatomical FDI order around each arch (patient right molar -> midline -> left
# molar). Third molars (x8) are omitted because most scans do not include them.
_MAXILLARY_ARCH_ORDER = (
    "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27",
)
_MANDIBULAR_ARCH_ORDER = (
    "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37",
)

# A tooth region with fewer triangles than this is too sparse to be real.
_MIN_TRIANGLES_PER_TOOTH = 4
# Arc-height profile resolution: this many buckets per expected tooth.
_BUCKETS_PER_TOOTH = 6
# Confidence stays capped below 1.0: even valley cuts are a draft, not a measurement.
_MAX_CONFIDENCE = 0.8
_MIN_CONFIDENCE = 0.25


def default_arch_order(arch: ArchName) -> tuple[str, ...]:
    """Anatomical FDI ordering used to label sectors around the given arch."""

    return _MAXILLARY_ARCH_ORDER if arch == "maxillary" else _MANDIBULAR_ARCH_ORDER


@dataclass(frozen=True)
class ToothSegment:
    """One proposed per-tooth region: its triangles, centroid, and confidence."""

    tooth_value: str
    triangles: list[Triangle]
    centroid: Vec3
    confidence: float

    @property
    def vertex_count(self) -> int:
        return len(self.triangles) * 3


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


def _segment_confidence(index: int, proms: list[float], max_prom: float) -> float:
    """Confidence from the prominence of a tooth's two bounding valleys."""

    if max_prom <= 0:
        return _MIN_CONFIDENCE
    left = proms[index - 1] if index > 0 else max_prom
    right = proms[index] if index < len(proms) else max_prom
    ratio = min(left, right) / max_prom
    value = _MIN_CONFIDENCE + (_MAX_CONFIDENCE - _MIN_CONFIDENCE) * ratio
    return round(min(_MAX_CONFIDENCE, max(_MIN_CONFIDENCE, value)), 3)


def auto_segment_arch(
    vertices: list[Vec3],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
) -> list[ToothSegment]:
    """Partition whole-arch triangles into anatomically ordered per-tooth regions.

    Cuts fall at the valleys between crowns. Returns ``[]`` when there is too
    little geometry to split meaningfully.
    """

    facets = _facets(vertices)
    teeth = tooth_values or default_arch_order(arch)
    n = len(teeth)
    if len(facets) < n * _MIN_TRIANGLES_PER_TOOTH:
        return []

    centroids = [_tri_centroid(f) for f in facets]
    cx = sum(c[0] for c in centroids) / len(centroids)
    cy = sum(c[1] for c in centroids) / len(centroids)
    angles = [atan2(c[1] - cy, c[0] - cx) for c in centroids]
    positions = arc_positions(angles, wrap_origin(angles))
    heights = [c[2] for c in centroids]

    buckets = n * _BUCKETS_PER_TOOTH
    profile, lo, span = height_profile(positions, heights, buckets)
    boundaries = find_boundaries(profile, n - 1)
    boundary_buckets = [bucket for bucket, _ in boundaries]
    proms = [prominence for _, prominence in boundaries]
    max_prom = max(proms) if proms else 0.0

    groups: list[list[int]] = [[] for _ in range(n)]
    for i, position in enumerate(positions):
        seg = bisect_right(boundary_buckets, bucket_of(position, lo, span, buckets))
        groups[min(seg, n - 1)].append(i)

    segments: list[ToothSegment] = []
    for index, indices in enumerate(groups):
        if not indices:
            continue
        segments.append(
            ToothSegment(
                tooth_value=teeth[index],
                triangles=[facets[i] for i in indices],
                centroid=_mean3([centroids[i] for i in indices]),
                confidence=_segment_confidence(index, proms, max_prom),
            )
        )
    return segments
