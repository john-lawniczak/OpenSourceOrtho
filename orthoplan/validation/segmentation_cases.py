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

from orthoplan.segmentation.auto import load_local_segmenter
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
    """Measure the cost of a missing tooth (the labelling cascade).

    The segmenter currently assumes the full canonical FDI arch, so an extraction
    gap is mislabelled: ``observed_tooth_count`` stays at the canonical count
    while fewer crowns exist (``tooth_count_error`` > 0). This case GATES that the
    geometry still separates cleanly (purity) and most teeth keep a correct label,
    and RECORDS the count error so a future data-driven tooth-count fix shows up
    as ``tooth_count_error`` -> 0. Tighten the count expectation once that lands.
    """

    case_id = "segmentation-missing-tooth"
    teeth = tuple(t for t in full_arch_truth(_ARCH) if t != _EXTRACTED_TOOTH)
    arch = build_synthetic_arch(teeth)
    segments = load_local_segmenter().segment(arch.vertices, arch=_ARCH)
    score = score_segmentation(segments, arch)
    count_error = abs(score.observed_count - score.expected_count)

    min_region_purity = 0.78
    min_labels_recovered = score.expected_count - 1
    expected: dict[str, MeasurementValue] = {
        "true_tooth_count": score.expected_count,
        "min_region_purity": min_region_purity,
        "min_labels_recovered": min_labels_recovered,
    }
    observed: dict[str, MeasurementValue] = {
        "observed_tooth_count": score.observed_count,
        "tooth_count_error": count_error,
        "region_purity": score.region_purity,
        "labels_recovered": score.labels_recovered,
        "triangle_label_accuracy": score.triangle_label_accuracy,
    }

    failures: list[str] = []
    if score.region_purity < min_region_purity:
        failures.append(
            f"region purity {score.region_purity} below floor {min_region_purity}"
        )
    if score.labels_recovered < min_labels_recovered:
        failures.append(
            f"labels recovered {score.labels_recovered} below floor {min_labels_recovered}"
        )
    return result(case_id, failures, expected=expected, observed=observed)
