from __future__ import annotations

from dataclasses import replace

from orthoplan.segmentation.heuristic import ToothSegment, _facets
from orthoplan.validation import run_measurement_lab
from orthoplan.validation.segmentation_truth import (
    build_synthetic_arch,
    full_arch_truth,
    score_segmentation,
)


def _segments_from_truth(arch) -> list[ToothSegment]:
    """A perfect segmentation: each true tooth becomes its own region."""

    by_tooth: dict[str, list] = {tooth: [] for tooth in arch.tooth_values}
    for tri in _facets(arch.vertices):
        centroid = (
            (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
            (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
            (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
        )
        key = (round(centroid[0] * 1e6), round(centroid[1] * 1e6), round(centroid[2] * 1e6))
        by_tooth[arch.truth_by_centroid[key]].append(tri)
    return [
        ToothSegment(tooth_value=tooth, triangles=tris, centroid=(0.0, 0.0, 0.0), confidence=0.5)
        for tooth, tris in by_tooth.items()
    ]


def test_build_synthetic_arch_shapes() -> None:
    teeth = full_arch_truth("maxillary")
    arch = build_synthetic_arch(teeth, tris_per_tooth=10)
    assert arch.expected_count == len(teeth)
    # 10 triangles per tooth, 3 vertices per triangle.
    assert len(arch.vertices) == len(teeth) * 10 * 3
    assert len(arch.truth_by_centroid) == len(teeth) * 10
    assert set(arch.truth_by_centroid.values()) == set(teeth)


def test_perfect_segmentation_scores_one() -> None:
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    score = score_segmentation(_segments_from_truth(arch), arch)
    assert score.triangle_label_accuracy == 1.0
    assert score.region_purity == 1.0
    assert score.observed_count == score.expected_count
    assert score.labels_recovered == score.expected_count


def test_relabelled_region_keeps_purity_but_loses_label_accuracy() -> None:
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    perfect = _segments_from_truth(arch)
    # Mislabel one region: swap its FDI value to a wrong-but-valid tooth. The
    # region is still pure (one true tooth), but its label is now wrong.
    wrong = [replace(seg, tooth_value="99") if i == 3 else seg for i, seg in enumerate(perfect)]
    score = score_segmentation(wrong, arch)
    assert score.region_purity == 1.0  # geometry unchanged
    assert score.triangle_label_accuracy < 1.0  # one region now mislabelled
    assert score.labels_recovered == score.expected_count - 1


def test_empty_segmentation_scores_zero() -> None:
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    score = score_segmentation([], arch)
    assert score.triangle_label_accuracy == 0.0
    assert score.region_purity == 0.0
    assert score.observed_count == 0


def test_full_arch_case_passes_and_records_metrics() -> None:
    result = run_measurement_lab("segmentation-full-arch-accuracy")[0]
    assert result.passed is True
    assert result.observed["observed_tooth_count"] == result.expected["expected_tooth_count"]
    assert result.observed["region_purity"] >= result.expected["min_region_purity"]
    assert result.observed["triangle_label_accuracy"] >= result.expected["min_triangle_label_accuracy"]


def test_missing_tooth_case_records_count_error() -> None:
    result = run_measurement_lab("segmentation-missing-tooth")[0]
    assert result.passed is True
    # Documents the current cascade: the segmenter forces the canonical count, so
    # a missing tooth shows up as a nonzero count error. When data-driven counting
    # lands this should fall to 0 and this expectation can tighten.
    assert result.observed["tooth_count_error"] >= 1
    assert result.observed["region_purity"] >= result.expected["min_region_purity"]


def test_segmentation_cases_registered_in_lab() -> None:
    ids = {r.case_id for r in run_measurement_lab()}
    assert {"segmentation-full-arch-accuracy", "segmentation-missing-tooth"} <= ids
