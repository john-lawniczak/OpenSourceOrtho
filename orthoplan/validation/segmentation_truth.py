"""Segmentation accuracy harness: score a proposal against known ground truth.

The on-device tooth segmenter (``orthoplan/segmentation``) produces reviewable
per-tooth proposals, but nothing measured whether a proposed cut landed on the
right boundary or carried the right FDI label. This module supplies that metric:
run the active segmenter on a synthetic arch whose per-triangle tooth membership
is known by construction (see ``synthetic_arch``) and score the result.

The arch is synthetic (not a real labelled scan) because real intraoral scans are
PHI, large, and expensive to hand-label; a placed arch gives exact, PHI-free,
deterministic truth and a fast CI gate. Real-scan benchmarking is a heavier,
separate offline effort - this harness is the measurable floor that lets later
segmenter changes prove a gain instead of merely changing the output.

The headline metric is ``triangle_label_accuracy``: the fraction of surface
triangles assigned to the correct tooth (overlap-style, capturing both
mislabelling and boundary drift in one number).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, pi, tau

from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import ToothSegment

# Re-exported so existing callers/tests keep importing arch construction from
# here; the construction itself now lives in ``synthetic_arch``.
from orthoplan.validation.synthetic_arch import (  # noqa: F401
    SyntheticArch,
    build_synthetic_arch,
    full_arch_truth,
    realistic_widths,
)
from orthoplan.validation.synthetic_arch import _centroid_key


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


def _mean3(tri: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


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
