"""Measurement Truth Lab runner.

Built-in synthetic cases exercise the public engine path and compare outputs
against known measurements with explicit tolerances. Golden fixtures live under
``orthoplan/validation/golden_fixtures`` and contain no patient data.
"""

from __future__ import annotations

from collections.abc import Callable

from orthoplan.validation import measurement_cases as cases
from orthoplan.validation import segmentation_cases as seg_cases
from orthoplan.validation import segmentation_compactness_case as seg_compactness
from orthoplan.validation.measurement_models import MeasurementTruthResult

CaseFn = Callable[[], MeasurementTruthResult]


def measurement_truth_cases() -> dict[str, CaseFn]:
    return {
        "golden-stl-bounds": cases.golden_stl_bounds,
        "golden-stl-degenerate": cases.golden_stl_degenerate,
        "bounds-known-ascii": cases.bounds_known_ascii,
        "cumulative-translation": cases.cumulative_translation,
        "known-mm-degree-transform": cases.known_mm_degree_transform,
        "rotation-gating": cases.rotation_gating,
        "movement-cap-resultant": cases.movement_cap_resultant,
        "segmentation-linkage": cases.segmentation_linkage,
        "segmentation-full-arch-accuracy": seg_cases.segmentation_full_arch_accuracy,
        "segmentation-realistic-arch-accuracy": seg_cases.segmentation_realistic_arch_accuracy,
        "segmentation-missing-tooth": seg_cases.segmentation_missing_tooth,
        "segmentation-open-gap": seg_cases.segmentation_open_gap,
        "segmentation-missing-tooth-marked": seg_cases.segmentation_missing_tooth_marked,
        "segmentation-crown-compactness": seg_compactness.segmentation_crown_compactness,
        "report-reproducibility": cases.report_reproducibility,
    }


def run_measurement_lab(case_id: str | None = None) -> list[MeasurementTruthResult]:
    all_cases = measurement_truth_cases()
    selected = {case_id: all_cases[case_id]} if case_id else all_cases
    return [fn() for fn in selected.values()]
