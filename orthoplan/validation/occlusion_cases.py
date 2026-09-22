"""Measurement Truth Lab case for bite registration accuracy.

Builds an opposing arch pair with a KNOWN occlusal gap and midline offset in a
shared frame (the as-scanned case a real registered export presents) and checks
that ``register_bite`` recovers them: it must report the as-scanned mode, recover
the gap and midline within tolerance, find the arches occluding across their shared
footprint, and not invent deep interpenetration. A regression in the occlusal grid
or the registration metrics moves these numbers and trips the gate.
"""

from __future__ import annotations

from orthoplan.occlusion import register_bite
from orthoplan.validation.measurement_models import (
    MeasurementTruthResult,
    MeasurementValue,
    close,
    result,
)
from orthoplan.validation.occlusion_truth import build_occluding_arches

_TRUE_GAP_MM = 0.4
_TRUE_MIDLINE_MM = 1.5


def occlusion_registration_accuracy() -> MeasurementTruthResult:
    """Gate that bite registration recovers a known as-scanned occlusal relationship."""

    case_id = "occlusion-registration-accuracy"
    upper, lower, _truth = build_occluding_arches(
        gap_mm=_TRUE_GAP_MM, midline_offset_mm=_TRUE_MIDLINE_MM
    )
    reg = register_bite(upper, lower)

    gap_tolerance = 0.15
    midline_tolerance = 0.2
    min_coverage = 0.85
    max_interpenetration = 0.5
    min_contact_fraction = 0.85
    expected: dict[str, MeasurementValue] = {
        "mode": "as-scanned",
        "true_gap_mm": _TRUE_GAP_MM,
        "true_midline_offset_mm": _TRUE_MIDLINE_MM,
        "min_coverage": min_coverage,
        "max_interpenetration_mm": max_interpenetration,
        "min_contact_fraction": min_contact_fraction,
    }
    observed: dict[str, MeasurementValue] = {
        "mode": reg.mode,
        "approximate": reg.approximate,
        "occlusal_gap_mm": reg.occlusal_gap_mm,
        "midline_offset_mm": reg.midline_offset_mm,
        "interpenetration_mm": reg.interpenetration_mm,
        "contact_fraction": reg.contact_fraction,
        "coverage": reg.coverage,
        "confidence": reg.confidence,
    }

    failures: list[str] = []
    if reg.mode != "as-scanned":
        failures.append(f"expected as-scanned registration, got {reg.mode}")
    close(reg.occlusal_gap_mm, _TRUE_GAP_MM, gap_tolerance, "occlusal gap", failures)
    close(reg.midline_offset_mm, _TRUE_MIDLINE_MM, midline_tolerance, "midline offset", failures)
    if reg.coverage < min_coverage:
        failures.append(f"coverage {reg.coverage} below floor {min_coverage}")
    if reg.interpenetration_mm > max_interpenetration:
        failures.append(
            f"interpenetration {reg.interpenetration_mm} above ceiling {max_interpenetration}"
        )
    if reg.contact_fraction < min_contact_fraction:
        failures.append(
            f"contact fraction {reg.contact_fraction} below floor {min_contact_fraction}"
        )
    return result(case_id, failures, expected=expected, observed=observed)
