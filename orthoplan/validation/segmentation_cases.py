"""Measurement Truth Lab cases for tooth-segmentation accuracy.

These run the ACTIVE on-device segmenter (``load_local_segmenter``) against a
synthetic arch whose per-triangle tooth membership is known by construction (see
``segmentation_truth``), so a change to the segmenter shows up as a measurable
move in these numbers instead of an unverifiable difference in output.

Thresholds are regression FLOORS set just below the current deterministic
baseline: a drop in quality trips the gate, while a genuine improvement passes
freely and is visible in the recorded ``observed`` metrics.
"""

from __future__ import annotations

from orthoplan.segmentation.auto import load_local_segmenter, tooth_values_for_arch
from orthoplan.validation.measurement_models import (
    MeasurementTruthResult,
    MeasurementValue,
    result,
)
from orthoplan.validation.segmentation_truth import (
    build_synthetic_arch,
    full_arch_truth,
    score_segmentation,
)

# Cases author a single arch; maxillary and mandibular score identically on the
# synthetic horseshoe, so one arch is enough to gate the shared algorithm.
_ARCH = "maxillary"
# A tooth removed to simulate an extraction gap (a real, common scan condition).
_EXTRACTED_TOOTH = "15"


def segmentation_full_arch_accuracy() -> MeasurementTruthResult:
    """Gate segmenter accuracy on a clean, complete synthetic arch."""

    case_id = "segmentation-full-arch-accuracy"
    arch = build_synthetic_arch(full_arch_truth(_ARCH))
    segments = load_local_segmenter().segment(arch.vertices, arch=_ARCH)
    score = score_segmentation(segments, arch)

    min_region_purity = 0.78
    min_label_accuracy = 0.55
    expected: dict[str, MeasurementValue] = {
        "expected_tooth_count": score.expected_count,
        "min_region_purity": min_region_purity,
        "min_triangle_label_accuracy": min_label_accuracy,
    }
    observed: dict[str, MeasurementValue] = {
        "observed_tooth_count": score.observed_count,
        "region_purity": score.region_purity,
        "triangle_label_accuracy": score.triangle_label_accuracy,
        "mean_centroid_arc_error_deg": score.mean_centroid_arc_error_deg,
    }

    failures: list[str] = []
    if score.observed_count != score.expected_count:
        failures.append(
            f"tooth count: expected {score.expected_count}, got {score.observed_count}"
        )
    if score.region_purity < min_region_purity:
        failures.append(
            f"region purity {score.region_purity} below floor {min_region_purity}"
        )
    if score.triangle_label_accuracy < min_label_accuracy:
        failures.append(
            f"label accuracy {score.triangle_label_accuracy} below floor {min_label_accuracy}"
        )
    return result(case_id, failures, expected=expected, observed=observed)


def segmentation_missing_tooth() -> MeasurementTruthResult:
    """A missing tooth must yield the right COUNT and clean regions.

    The segmenter detects the number of crowns from the arch's height valleys
    instead of assuming the canonical count, so an arch with a tooth absent is
    segmented into the correct number of regions (``tooth_count_error == 0``) and
    those regions stay clean (purity), rather than fabricating an extra split.

    ``triangle_label_accuracy`` is recorded but deliberately NOT gated here: which
    tooth is absent cannot be known from crown geometry alone, so without a user
    signal the FDI labels on a gap arch are a positional guess (confidence is
    lowered and the API raises a review advisory). The ``-marked`` case below shows
    that signal closing the gap; this case proves the count/region win on its own.
    """

    case_id = "segmentation-missing-tooth"
    teeth = tuple(t for t in full_arch_truth(_ARCH) if t != _EXTRACTED_TOOTH)
    arch = build_synthetic_arch(teeth)
    segments = load_local_segmenter().segment(arch.vertices, arch=_ARCH)
    score = score_segmentation(segments, arch)
    count_error = abs(score.observed_count - score.expected_count)

    min_region_purity = 0.80
    expected: dict[str, MeasurementValue] = {
        "true_tooth_count": score.expected_count,
        "max_tooth_count_error": 0,
        "min_region_purity": min_region_purity,
    }
    observed: dict[str, MeasurementValue] = {
        "observed_tooth_count": score.observed_count,
        "tooth_count_error": count_error,
        "region_purity": score.region_purity,
        "labels_recovered": score.labels_recovered,
        "triangle_label_accuracy": score.triangle_label_accuracy,
    }

    failures: list[str] = []
    if count_error != 0:
        failures.append(
            f"tooth count error {count_error}: detected {score.observed_count} "
            f"for {score.expected_count} crowns"
        )
    if score.region_purity < min_region_purity:
        failures.append(
            f"region purity {score.region_purity} below floor {min_region_purity}"
        )
    return result(case_id, failures, expected=expected, observed=observed)


def segmentation_open_gap() -> MeasurementTruthResult:
    """An open extraction site (gum-filled hole) is counted correctly.

    A real extraction leaves a one-tooth-wide hole filled with low gum, not evenly
    respaced teeth. That wide valley is the case that tempted the counter to
    over-count (its two shoulders look like two cuts). Counting crown PEAKS instead
    of valleys handles it: the gum hole has no peak, so the count stays correct
    (``tooth_count_error == 0``) and the present crowns segment cleanly (purity).
    Records label accuracy (unmarked, a positional guess - the user can mark the
    gap to recover it, as in the -marked case).
    """

    case_id = "segmentation-open-gap"
    arch = build_synthetic_arch(full_arch_truth(_ARCH), gaps=(_EXTRACTED_TOOTH,))
    segments = load_local_segmenter().segment(arch.vertices, arch=_ARCH)
    score = score_segmentation(segments, arch)
    count_error = abs(score.observed_count - score.expected_count)

    min_region_purity = 0.78
    expected: dict[str, MeasurementValue] = {
        "present_tooth_count": score.expected_count,
        "max_tooth_count_error": 0,
        "min_region_purity": min_region_purity,
    }
    observed: dict[str, MeasurementValue] = {
        "observed_tooth_count": score.observed_count,
        "tooth_count_error": count_error,
        "region_purity": score.region_purity,
        "triangle_label_accuracy": score.triangle_label_accuracy,
    }

    failures: list[str] = []
    if count_error != 0:
        failures.append(
            f"open-gap tooth count error {count_error}: detected "
            f"{score.observed_count} for {score.expected_count} present crowns"
        )
    if score.region_purity < min_region_purity:
        failures.append(
            f"region purity {score.region_purity} below floor {min_region_purity}"
        )
    return result(case_id, failures, expected=expected, observed=observed)


def segmentation_missing_tooth_marked() -> MeasurementTruthResult:
    """Marking the missing tooth restores correct FDI labels on a gap arch.

    Same gap arch as ``segmentation-missing-tooth``, but the user marks which tooth
    is absent, so the regions are labelled by the canonical order minus that tooth.
    ``triangle_label_accuracy`` should recover from the unmarked positional guess
    (~0.19) back to full-arch quality - that is the user signal turning the label
    drop into a gain. Gated against the unmarked baseline to stay self-calibrating.
    """

    case_id = "segmentation-missing-tooth-marked"
    teeth = tuple(t for t in full_arch_truth(_ARCH) if t != _EXTRACTED_TOOTH)
    arch = build_synthetic_arch(teeth)
    segmenter = load_local_segmenter()

    marked = score_segmentation(
        segmenter.segment(
            arch.vertices,
            arch=_ARCH,
            tooth_values=tooth_values_for_arch(_ARCH, [_EXTRACTED_TOOTH]),
        ),
        arch,
    )
    unmarked = score_segmentation(segmenter.segment(arch.vertices, arch=_ARCH), arch)

    min_label_accuracy = 0.55
    expected: dict[str, MeasurementValue] = {
        "true_tooth_count": marked.expected_count,
        "min_triangle_label_accuracy": min_label_accuracy,
        "must_beat_unmarked": True,
    }
    observed: dict[str, MeasurementValue] = {
        "observed_tooth_count": marked.observed_count,
        "marked_triangle_label_accuracy": marked.triangle_label_accuracy,
        "unmarked_triangle_label_accuracy": unmarked.triangle_label_accuracy,
        "region_purity": marked.region_purity,
    }

    failures: list[str] = []
    if marked.observed_count != marked.expected_count:
        failures.append(
            f"tooth count {marked.observed_count} != {marked.expected_count}"
        )
    if marked.triangle_label_accuracy < min_label_accuracy:
        failures.append(
            f"label accuracy {marked.triangle_label_accuracy} below floor {min_label_accuracy}"
        )
    if marked.triangle_label_accuracy <= unmarked.triangle_label_accuracy:
        failures.append(
            f"marking the gap did not improve labels: marked "
            f"{marked.triangle_label_accuracy} <= unmarked {unmarked.triangle_label_accuracy}"
        )
    return result(case_id, failures, expected=expected, observed=observed)
