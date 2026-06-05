"""Measurement Truth Lab runner.

Built-in synthetic cases exercise the public engine path and compare outputs
against known measurements with explicit tolerances. Golden fixtures live under
``orthoplan/validation/golden_fixtures`` and contain no patient data.
"""

from __future__ import annotations

from collections.abc import Callable

from orthoplan.validation import measurement_cases as cases
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
        "report-reproducibility": cases.report_reproducibility,
    }


def run_measurement_lab(case_id: str | None = None) -> list[MeasurementTruthResult]:
    all_cases = measurement_truth_cases()
    selected = {case_id: all_cases[case_id]} if case_id else all_cases
    return [fn() for fn in selected.values()]
