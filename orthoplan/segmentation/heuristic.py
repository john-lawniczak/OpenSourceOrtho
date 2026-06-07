"""Heuristic whole-arch tooth segmentation (dependency-free, deterministic).

This is NOT machine learning and NOT clinical. It partitions a whole-arch scan
into per-tooth regions by walking the dental arch in the occlusal plane (z is the
occlusogingival axis, see model.geometry) and splitting it into anatomically
ordered angular sectors around the arch centroid.

The output is an APPROXIMATE proposal that must be reviewed and corrected by a
human. Per-tooth ``confidence`` reflects only how cleanly a sector separated from
its neighbours - never clinical certainty, tooth identity, or treatment validity.

A real on-device learned model (e.g. a Teeth3DS / MeshSegNet network) can replace
this behind the same :class:`ToothSegment` contract; see ``segmentation/auto.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2
from statistics import median

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]

# Anatomical FDI order around each arch (patient right molar -> midline -> left
# molar). Third molars (x8) are omitted because most scans do not include them.
_MAXILLARY_ARCH_ORDER = (
    "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27",
)
_MANDIBULAR_ARCH_ORDER = (
    "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37",
)

# A sector with fewer triangles than this is too sparse to be a real crown region.
_MIN_TRIANGLES_PER_TOOTH = 4
# Heuristic confidence is intentionally capped low: this is a rough proposal.
_MAX_CONFIDENCE = 0.6
_MIN_CONFIDENCE = 0.2


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


def _equal_count_bins(order: list[int], n: int) -> list[list[int]]:
    """Split ``order`` into ``n`` contiguous, near-equal-sized chunks."""

    total = len(order)
    bins: list[list[int]] = []
    start = 0
    for k in range(n):
        end = round((k + 1) * total / n)
        bins.append(order[start:end])
        start = end
    return bins


def _confidence(span: float, median_span: float) -> float:
    """Confidence from how close a sector's angular width is to the median."""

    if median_span <= 0:
        return _MIN_CONFIDENCE
    deviation = min(1.0, abs(span - median_span) / median_span)
    return round(max(_MIN_CONFIDENCE, _MAX_CONFIDENCE - _MAX_CONFIDENCE * deviation), 3)


def auto_segment_arch(
    vertices: list[Vec3],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
) -> list[ToothSegment]:
    """Partition whole-arch triangles into anatomically ordered per-tooth sectors.

    Returns ``[]`` when there is too little geometry to split meaningfully.
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
    order = sorted(range(len(facets)), key=lambda i: angles[i])
    bins = _equal_count_bins(order, n)

    spans = [max(0.0, angles[b[-1]] - angles[b[0]]) for b in bins if b]
    median_span = median(spans) if spans else 0.0

    segments: list[ToothSegment] = []
    for tooth_value, indices in zip(teeth, bins):
        if not indices:
            continue
        tris = [facets[i] for i in indices]
        seg_centroids = [centroids[i] for i in indices]
        cen = (
            sum(c[0] for c in seg_centroids) / len(seg_centroids),
            sum(c[1] for c in seg_centroids) / len(seg_centroids),
            sum(c[2] for c in seg_centroids) / len(seg_centroids),
        )
        span = max(0.0, angles[indices[-1]] - angles[indices[0]])
        segments.append(
            ToothSegment(
                tooth_value=tooth_value,
                triangles=tris,
                centroid=cen,
                confidence=_confidence(span, median_span),
            )
        )
    return segments
