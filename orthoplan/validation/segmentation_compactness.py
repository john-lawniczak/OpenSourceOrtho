"""Intrinsic crown-compactness metric for segmentation proposals.

Unlike ``segmentation_truth`` (which scores produced regions against known
per-triangle truth), this metric needs NO ground truth. It measures how spatially
TIGHT each produced per-tooth region is, targeting the "rough wedge" failure mode:
the heuristic cuts the whole shell with a near-planar slice, so a region can sprawl
radially across the arch instead of hugging one compact crown. A learned backend
that follows the gingival margin and interproximal contacts produces tighter
regions and should score higher here.

Definition (deterministic, dependency-free): for each segment, the planar radius of
gyration of its triangle centroids (RMS distance to the segment centroid in the
occlusal plane) is compared to an arch-scale "expected crown radius" derived from
the whole-arch footprint and the number of regions. A region the size of one crown
scores near 1.0; a region sprawling across several crowns scores toward 0.

CAVEAT: a flat synthetic arch cannot fully express the wedge mode - it has crowns
but no deep gum skirt below them, so the worst sprawl (gum-to-crown vertical
slabs) does not appear. On synthetic data this is therefore a LOOSE tracking floor,
not a tight gate. The honest benchmark is a small labelled real-scan fixture kept
out of git (PHI / consent) - that is future work, recorded in
docs/segmentation-learned-backend.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import ToothSegment

# Compactness scales as expected_radius / (expected_radius + k * gyration): a region
# whose gyration equals the expected crown radius scores 1/(1+k). With k=1 a single
# tooth-sized region lands near 0.5 and a region sprawling across several crowns
# falls well below it, so the floor reads as "roughly one-crown-tight".
_GYRATION_WEIGHT = 1.0


@dataclass(frozen=True)
class CompactnessScore:
    """Intrinsic spatial tightness of a set of per-tooth regions."""

    segment_count: int
    mean_compactness: float
    min_compactness: float
    expected_crown_radius: float


def _tri_centroid(tri: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


def _planar_gyration(centroids: list[Vec3], center: Vec3) -> float:
    """RMS distance of ``centroids`` to ``center`` in the occlusal (xy) plane."""

    if not centroids:
        return 0.0
    total = 0.0
    for c in centroids:
        dx, dy = c[0] - center[0], c[1] - center[1]
        total += dx * dx + dy * dy
    return (total / len(centroids)) ** 0.5


def _expected_crown_radius(all_centroids: list[Vec3], reference_count: int) -> float:
    """Arch-scale single-crown radius from the whole-arch planar footprint.

    Half the per-crown span of the arch's bounding-box diagonal - the radius a
    compact, tooth-sized region would occupy if the arch were split evenly into
    ``reference_count`` crowns. ``reference_count`` is a FIXED reference (the
    expected/canonical tooth count), never the produced region count: otherwise a
    sprawling segmentation with fewer, bigger regions would inflate the expected
    radius and hide its own sprawl.
    """

    if not all_centroids or reference_count <= 0:
        return 0.0
    xs = [c[0] for c in all_centroids]
    ys = [c[1] for c in all_centroids]
    diagonal = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
    return diagonal / reference_count / 2.0


def score_compactness(
    segments: list[ToothSegment], *, expected_count: int | None = None
) -> CompactnessScore:
    """Score how spatially tight ``segments`` are (no ground truth required).

    ``expected_count`` anchors the per-crown radius to a fixed reference (the
    canonical arch tooth count). It defaults to the produced region count for ad-hoc
    use, but callers gating against sprawl should pass the true expected count so a
    region that swallows several crowns is penalised, not normalised away.
    """

    if not segments:
        return CompactnessScore(0, 0.0, 0.0, 0.0)

    per_segment_centroids: list[list[Vec3]] = [
        [_tri_centroid(tri) for tri in segment.triangles] for segment in segments
    ]
    all_centroids = [c for group in per_segment_centroids for c in group]
    expected_radius = _expected_crown_radius(
        all_centroids, expected_count if expected_count is not None else len(segments)
    )

    compactness: list[float] = []
    for segment, centroids in zip(segments, per_segment_centroids):
        if not centroids:
            continue
        gyration = _planar_gyration(centroids, segment.centroid)
        denom = expected_radius + _GYRATION_WEIGHT * gyration
        compactness.append(expected_radius / denom if denom > 0 else 1.0)

    if not compactness:
        return CompactnessScore(len(segments), 0.0, 0.0, round(expected_radius, 4))
    return CompactnessScore(
        segment_count=len(segments),
        mean_compactness=round(sum(compactness) / len(compactness), 4),
        min_compactness=round(min(compactness), 4),
        expected_crown_radius=round(expected_radius, 4),
    )
