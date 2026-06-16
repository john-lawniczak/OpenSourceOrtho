"""Deterministic quality gates for segmentation proposals.

The segmentation layer returns reviewable drafts. These gates make the difference
between "usable for human review" and "production candidate" explicit so a future
learned backend cannot quietly graduate on tooth count alone.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import ToothSegment, default_arch_order


class SegmentationQualityThresholds(BaseModel):
    """Thresholds for reviewable and production-candidate segmentation gates."""

    min_review_mean_compactness: float = 0.28
    min_review_min_compactness: float = 0.20
    min_production_mean_compactness: float = 0.45
    min_production_min_compactness: float = 0.35
    min_production_confidence: float = 0.60


class SegmentationQualityReport(BaseModel):
    """Gate report attached to a segmentation proposal or benchmark run."""

    arch: ArchName
    expected_tooth_count: int = Field(ge=0)
    observed_tooth_count: int = Field(ge=0)
    mean_compactness: float = Field(ge=0.0)
    min_compactness: float = Field(ge=0.0)
    min_confidence: float = Field(ge=0.0, le=1.0)
    reviewable: bool
    production_candidate: bool
    failed_checks: list[str] = Field(default_factory=list)
    production_blockers: list[str] = Field(default_factory=list)


def evaluate_segmentation_quality(
    segments: list[ToothSegment],
    *,
    arch: ArchName,
    expected_tooth_count: int | None = None,
    thresholds: SegmentationQualityThresholds | None = None,
) -> SegmentationQualityReport:
    """Evaluate hard gates for a per-arch segmentation proposal."""

    limits = thresholds or SegmentationQualityThresholds()
    expected = expected_tooth_count if expected_tooth_count is not None else len(default_arch_order(arch))
    mean_compactness, min_compactness = _score_compactness(segments, expected_count=expected)
    min_confidence = min((segment.confidence for segment in segments), default=0.0)

    failed: list[str] = []
    if len(segments) != expected:
        failed.append("tooth-count-mismatch")
    if mean_compactness < limits.min_review_mean_compactness:
        failed.append("mean-compactness-below-review-floor")
    if min_compactness < limits.min_review_min_compactness:
        failed.append("min-compactness-below-review-floor")
    if not segments:
        failed.append("no-segments")

    production_blockers = list(failed)
    if mean_compactness < limits.min_production_mean_compactness:
        production_blockers.append("mean-compactness-below-production-floor")
    if min_compactness < limits.min_production_min_compactness:
        production_blockers.append("min-compactness-below-production-floor")
    if min_confidence < limits.min_production_confidence:
        production_blockers.append("confidence-below-production-floor")

    return SegmentationQualityReport(
        arch=arch,
        expected_tooth_count=expected,
        observed_tooth_count=len(segments),
        mean_compactness=mean_compactness,
        min_compactness=min_compactness,
        min_confidence=round(min_confidence, 4),
        reviewable=not failed,
        production_candidate=not production_blockers,
        failed_checks=failed,
        production_blockers=production_blockers,
    )


def _score_compactness(segments: list[ToothSegment], *, expected_count: int) -> tuple[float, float]:
    if not segments:
        return 0.0, 0.0
    per_segment_centroids = [[_tri_centroid(tri) for tri in segment.triangles] for segment in segments]
    all_centroids = [centroid for group in per_segment_centroids for centroid in group]
    expected_radius = _expected_crown_radius(all_centroids, expected_count)
    scores: list[float] = []
    for segment, centroids in zip(segments, per_segment_centroids):
        if not centroids:
            continue
        gyration = _planar_gyration(centroids, segment.centroid)
        denom = expected_radius + gyration
        scores.append(expected_radius / denom if denom > 0 else 1.0)
    if not scores:
        return 0.0, 0.0
    return round(sum(scores) / len(scores), 4), round(min(scores), 4)


def _tri_centroid(tri: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


def _planar_gyration(centroids: list[Vec3], center: Vec3) -> float:
    if not centroids:
        return 0.0
    total = 0.0
    for centroid in centroids:
        dx, dy = centroid[0] - center[0], centroid[1] - center[1]
        total += dx * dx + dy * dy
    return (total / len(centroids)) ** 0.5


def _expected_crown_radius(all_centroids: list[Vec3], reference_count: int) -> float:
    if not all_centroids or reference_count <= 0:
        return 0.0
    xs = [centroid[0] for centroid in all_centroids]
    ys = [centroid[1] for centroid in all_centroids]
    diagonal = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
    return diagonal / reference_count / 2.0
