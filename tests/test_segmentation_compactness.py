"""Crown-compactness metric: tight regions score higher than sprawling ones.

This is the intrinsic (no-ground-truth) metric that makes the "rough wedge" failure
mode measurable - a region can carry the right FDI label yet still sprawl across the
arch. The synthetic arch understates the mode (no gum skirt), so the lab case is a
loose tracking floor; these tests pin the metric's direction and its gate.
"""

from __future__ import annotations

from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.heuristic import ToothSegment, default_arch_order
from orthoplan.validation import run_measurement_lab
from orthoplan.validation.segmentation_compactness import score_compactness
from orthoplan.validation.segmentation_truth import build_synthetic_arch, full_arch_truth


def test_empty_segments_score_zero() -> None:
    score = score_compactness([])
    assert score.segment_count == 0 and score.mean_compactness == 0.0


def test_sprawling_region_scores_below_tight_regions() -> None:
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    segments = load_local_segmenter().segment(arch.vertices, arch="maxillary")
    expected_count = len(default_arch_order("maxillary"))

    tight = score_compactness(segments, expected_count=expected_count)

    # Merge three adjacent crowns into one sprawling region (a wedge across the arch).
    merged = ToothSegment(
        "99",
        segments[0].triangles + segments[1].triangles + segments[2].triangles,
        segments[0].centroid,
        0.5,
    )
    sprawled = score_compactness([merged, *segments[3:]], expected_count=expected_count)

    assert sprawled.min_compactness < tight.min_compactness
    assert sprawled.mean_compactness < tight.mean_compactness


def test_crown_compactness_case_passes_for_current_segmenter() -> None:
    result = run_measurement_lab("segmentation-crown-compactness")[0]
    assert result.case_id == "segmentation-crown-compactness"
    assert result.passed is True
    assert result.observed["mean_compactness"] >= result.expected["min_mean_compactness"]
