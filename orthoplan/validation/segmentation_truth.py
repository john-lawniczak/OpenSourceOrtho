"""Segmentation accuracy harness: synthetic arches with known ground truth.

The on-device tooth segmenter (``orthoplan/segmentation``) produced reviewable
per-tooth proposals, but nothing measured whether a proposed cut landed on the
right boundary or carried the right FDI label. This module supplies that missing
metric, following the Measurement Truth Lab pattern: build a synthetic whole-arch
mesh whose per-triangle tooth membership is known by construction, run the active
segmenter, and score the result against the known truth.

Why synthetic (not a real labelled scan): real intraoral scans are PHI, large,
and expensive to hand-label precisely. A placed arch gives an exact, PHI-free,
deterministic ground truth and a fast CI gate. Real-scan benchmarking is a
heavier, separate offline effort; this harness is the measurable floor that lets
later segmenter changes prove a gain instead of merely changing the output.

The headline metric is ``triangle_label_accuracy``: the fraction of surface
triangles the segmenter assigned to the correct tooth. It is overlap-style
(IoU-like) and captures both mislabelling and boundary drift in one number.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, pi, sin, tau

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import ToothSegment, default_arch_order

# Horseshoe geometry for the synthetic arch. Teeth span less than a full turn so
# there is an explicit opening gap at the back (the segmenter's wrap-origin logic
# expects the largest angular gap to be the mouth opening, not an embrasure).
_ARCH_SPAN = 1.6 * pi
_RADIUS = 22.0
_CROWN_HEIGHT = 9.0
_VALLEY_HEIGHT = 3.0
# Open extraction sites are filled with a flat "gum" surface below the inter-crown
# valleys, so the hole reads as the deepest, widest valley on the arch.
_GUM_HEIGHT_RATIO = 0.4
# Triangles per tooth. Each tooth's triangles span the inner 90% of its sector,
# leaving a 10% no-triangle embrasure so a height valley forms between crowns.
_TRIS_PER_TOOTH = 16
_SECTOR_FILL = 0.9
# A tiny in-plane triangle whose three offsets sum to zero, so its centroid is
# exactly the placed point and recomputing it (mean of vertices) is loss-free.
_TRI_OFFSETS: tuple[Vec3, ...] = (
    (0.06, 0.0, 0.0),
    (-0.03, 0.052, 0.0),
    (-0.03, -0.052, 0.0),
)


def _centroid_key(point: Vec3) -> tuple[int, int, int]:
    """Hashable identity for a triangle centroid, robust to float noise."""

    return (round(point[0] * 1e6), round(point[1] * 1e6), round(point[2] * 1e6))


@dataclass(frozen=True)
class SyntheticArch:
    """A placed whole-arch mesh plus the true tooth label of every triangle."""

    vertices: list[Vec3]
    # True tooth value keyed by triangle-centroid identity.
    truth_by_centroid: dict[tuple[int, int, int], str]
    tooth_values: tuple[str, ...]
    # True center arc-position (radians from the arch origin) per tooth value.
    arc_center: dict[str, float]

    @property
    def expected_count(self) -> int:
        return len(self.tooth_values)


def build_synthetic_arch(
    tooth_values: tuple[str, ...],
    *,
    gaps: tuple[str, ...] = (),
    radius: float = _RADIUS,
    crown_height: float = _CROWN_HEIGHT,
    valley_height: float = _VALLEY_HEIGHT,
    tris_per_tooth: int = _TRIS_PER_TOOTH,
) -> SyntheticArch:
    """Place ``tooth_values`` as cosine crowns around a horseshoe.

    Each tooth is a cluster of small triangles at a known arc sector; height peaks
    at the sector center and falls to ``valley_height`` at the edges, so the
    embrasures between teeth read as valleys to the segmenter.

    ``gaps`` models open EXTRACTION sites: a listed tooth keeps its full-arch
    sector position but is filled with a flat, low "gum" surface (below the
    inter-crown valleys) instead of a crown, leaving a real one-tooth-wide hole.
    The gap's triangles carry no ground-truth tooth (they are not a crown), and
    the arch's ``tooth_values`` are the teeth actually present.
    """

    n = len(tooth_values)
    sector = _ARCH_SPAN / n
    start = -_ARCH_SPAN / 2.0
    gap_set = set(gaps)
    gum_height = valley_height * _GUM_HEIGHT_RATIO
    vertices: list[Vec3] = []
    truth: dict[tuple[int, int, int], str] = {}
    arc_center: dict[str, float] = {}
    present: list[str] = []

    for i, tooth in enumerate(tooth_values):
        center = start + (i + 0.5) * sector
        is_gap = tooth in gap_set
        half = 0.5 * _SECTOR_FILL * sector
        for t in range(tris_per_tooth):
            # Local offset in [-half, half] across the sector.
            frac = (t / (tris_per_tooth - 1)) - 0.5 if tris_per_tooth > 1 else 0.0
            theta = center + frac * 2.0 * half
            # Crown: cos peak. Gap: flat gum floor below the inter-crown valleys.
            height = gum_height if is_gap else valley_height + (crown_height - valley_height) * cos(frac * pi)
            cx = radius * cos(theta)
            cy = radius * sin(theta)
            centroid: Vec3 = (cx, cy, height)
            if not is_gap:
                truth[_centroid_key(centroid)] = tooth
            for off in _TRI_OFFSETS:
                vertices.append((cx + off[0], cy + off[1], height + off[2]))
        if not is_gap:
            arc_center[tooth] = center
            present.append(tooth)

    return SyntheticArch(
        vertices=vertices,
        truth_by_centroid=truth,
        tooth_values=tuple(present),
        arc_center=arc_center,
    )


@dataclass(frozen=True)
class SegmentationScore:
    """Accuracy of a segmentation proposal against a synthetic ground truth.

    Two complementary accuracy axes:

    - ``region_purity`` measures BOUNDARY quality: how cleanly each produced
      region maps to a single true tooth, independent of which FDI label it was
      given. It answers "did the cuts land between the right crowns?".
    - ``triangle_label_accuracy`` additionally requires the right FDI LABEL on
      the right region. The gap between purity and label accuracy is the cost of
      the segmenter's labelling step (fixed canonical FDI order), which is the
      first thing to drift when a tooth is missing.
    """

    expected_count: int
    observed_count: int
    triangle_label_accuracy: float
    region_purity: float
    labels_recovered: int
    mean_centroid_arc_error_deg: float


def _segment_centroid_angle(segment: ToothSegment, cx: float, cy: float) -> float:
    return atan2(segment.centroid[1] - cy, segment.centroid[0] - cx)


def _angle_error_deg(a: float, b: float) -> float:
    """Smallest absolute angular difference between two angles, in degrees."""

    diff = (a - b) % tau
    if diff > pi:
        diff = tau - diff
    return degrees(abs(diff))


def score_segmentation(segments: list[ToothSegment], arch: SyntheticArch) -> SegmentationScore:
    """Score produced ``segments`` against the synthetic ``arch`` ground truth."""

    truth = arch.truth_by_centroid
    total = 0
    correct = 0
    pure = 0
    for segment in segments:
        true_labels: list[str] = []
        for tri in segment.triangles:
            true_label = truth.get(_centroid_key(_mean3(tri)))
            if true_label is None:
                continue
            true_labels.append(true_label)
            total += 1
            if true_label == segment.tooth_value:
                correct += 1
        if true_labels:
            # Most common true tooth in this region = its dominant membership.
            dominant = max(set(true_labels), key=true_labels.count)
            pure += true_labels.count(dominant)

    accuracy = correct / total if total else 0.0
    purity = pure / total if total else 0.0

    produced_labels = {segment.tooth_value for segment in segments}
    labels_recovered = sum(1 for tooth in arch.tooth_values if tooth in produced_labels)

    # Mean arc error for produced labels that match a known tooth.
    cx = sum(v[0] for v in arch.vertices) / len(arch.vertices)
    cy = sum(v[1] for v in arch.vertices) / len(arch.vertices)
    errors: list[float] = []
    for segment in segments:
        center = arch.arc_center.get(segment.tooth_value)
        if center is None:
            continue
        produced_angle = _segment_centroid_angle(segment, cx, cy)
        errors.append(_angle_error_deg(produced_angle, center))
    mean_arc_error = sum(errors) / len(errors) if errors else 0.0

    return SegmentationScore(
        expected_count=arch.expected_count,
        observed_count=len(segments),
        triangle_label_accuracy=round(accuracy, 4),
        region_purity=round(purity, 4),
        labels_recovered=labels_recovered,
        mean_centroid_arc_error_deg=round(mean_arc_error, 3),
    )


def _mean3(tri: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


def full_arch_truth(arch: ArchName) -> tuple[str, ...]:
    """The canonical FDI tooth order the segmenter labels for a full arch."""

    return default_arch_order(arch)
