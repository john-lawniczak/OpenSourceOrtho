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


def test_missing_tooth_case_recovers_correct_count() -> None:
    result = run_measurement_lab("segmentation-missing-tooth")[0]
    assert result.passed is True
    # Data-driven counting: a missing tooth yields the right number of regions.
    assert result.observed["tooth_count_error"] == 0
    assert result.observed["observed_tooth_count"] == result.expected["true_tooth_count"]
    assert result.observed["region_purity"] >= result.expected["min_region_purity"]


def test_segmentation_cases_registered_in_lab() -> None:
    ids = {r.case_id for r in run_measurement_lab()}
    assert {"segmentation-full-arch-accuracy", "segmentation-missing-tooth"} <= ids


def test_build_synthetic_arch_models_an_open_gap() -> None:
    full = full_arch_truth("maxillary")
    arch = build_synthetic_arch(full, gaps=("15",))
    # The gap tooth is absent from the present set and from the ground truth.
    assert "15" not in arch.tooth_values
    assert arch.expected_count == len(full) - 1
    assert "15" not in set(arch.truth_by_centroid.values())
    # The other crowns keep their identities.
    assert set(arch.tooth_values) == set(t for t in full if t != "15")


def test_open_gap_is_counted_by_crown_peaks_not_valleys() -> None:
    # The whole point of the open-gap harness: detection counts the present crowns
    # (13), not 14 - a wide gum hole must not read as an extra tooth.
    result = run_measurement_lab("segmentation-open-gap")[0]
    assert result.passed is True
    assert result.observed["tooth_count_error"] == 0
    assert result.observed["observed_tooth_count"] == result.expected["present_tooth_count"]


def test_crown_peaks_not_valleys_are_counted() -> None:
    from orthoplan.segmentation.arch_profile import detect_cut_count

    # Three crowns (interior peaks), then a wide flat gum hole on the right. Counting
    # crown peaks sees exactly 3 crowns regardless of the hole; leading/trailing low
    # buckets keep the end crowns interior, as a real arch profile always ramps up.
    # (The valley over-count this avoids is proven end-to-end by the
    # segmentation-open-gap lab case.)
    profile = [1.0, 9.0, 3.0, 9.0, 3.0, 9.0, 1.0, 1.0, 1.0, 1.0]
    assert detect_cut_count(profile, max_cuts=14, find_minima=False) == 3


def test_resolve_tooth_count_floors_and_falls_back() -> None:
    from orthoplan.segmentation.heuristic import resolve_tooth_count

    # A flat profile has no crowns -> fall back to the canonical count.
    assert resolve_tooth_count([5.0] * 8, canonical=14) == 14
    # A clean full arch's worth of crowns is detected as the canonical count.
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    from orthoplan.segmentation.arch_profile import arc_signal, height_profile
    from orthoplan.segmentation.heuristic import _facets, _tri_centroid

    positions, heights = arc_signal([_tri_centroid(f) for f in _facets(arch.vertices)])
    profile = height_profile(positions, heights, 14 * 8)[0]
    assert resolve_tooth_count(profile, canonical=14) == 14


def test_marking_the_gap_recovers_label_accuracy() -> None:
    result = run_measurement_lab("segmentation-missing-tooth-marked")[0]
    assert result.passed is True
    # The user signal beats the unmarked positional guess and clears the floor.
    assert (
        result.observed["marked_triangle_label_accuracy"]
        > result.observed["unmarked_triangle_label_accuracy"]
    )
    assert (
        result.observed["marked_triangle_label_accuracy"]
        >= result.expected["min_triangle_label_accuracy"]
    )


def test_detect_cut_count_counts_real_valleys_not_a_fixed_number() -> None:
    from orthoplan.segmentation.arch_profile import detect_cut_count

    # Three crowns (peaks) separated by two deep valleys.
    profile = [9.0, 3.0, 9.0, 3.0, 9.0]
    assert detect_cut_count(profile, max_cuts=13) == 2
    # A flat profile carries no usable valleys -> 0 (caller falls back to canonical).
    assert detect_cut_count([5.0] * 8, max_cuts=13) == 0
    # max_cuts caps the result.
    assert detect_cut_count(profile, max_cuts=1) == 1


def test_detect_cut_count_finds_peaks_when_requested() -> None:
    from orthoplan.segmentation.arch_profile import detect_cut_count

    # Inverted signal: boundaries are peaks (hybrid cost signal).
    profile = [1.0, 8.0, 1.0, 8.0, 1.0]
    assert detect_cut_count(profile, max_cuts=13, find_minima=False) == 2


def test_count_advisory_only_fires_on_non_canonical_arch() -> None:
    from orthoplan.segmentation.auto import build_count_advisories
    from orthoplan.segmentation.heuristic import default_arch_order

    full = len(default_arch_order("maxillary"))
    assert build_count_advisories({"maxillary": full}) == []
    advisories = build_count_advisories({"maxillary": full - 1})
    assert len(advisories) == 1
    assert "review" in advisories[0].message.lower()
