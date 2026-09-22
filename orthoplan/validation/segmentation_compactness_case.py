"""Measurement Truth Lab case for crown-compactness (the "rough wedge" floor).

Runs the ACTIVE segmenter on the realistic synthetic arch and scores how tight its
per-tooth regions are (see ``segmentation_compactness``). It gates the failure mode
the accuracy cases cannot see: a region can be labelled correctly yet still sprawl
across the arch as a planar slice rather than hugging one crown.

The floors are set just below the current deterministic baseline, so a regression
that makes regions sprawl trips the gate while a tighter (e.g. learned) backend
passes and shows the gain in the recorded metrics.

CAVEAT (intentional, not a bug): a flat synthetic arch understates the wedge mode -
it has crowns but no deep gum skirt below them - so this is a LOOSE tracking floor.
A small labelled real-scan fixture (PHI/consent, kept out of git) is the honest
benchmark and is future work; see docs/segmentation-learned-backend.md.
"""

from __future__ import annotations

from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.heuristic import default_arch_order
from orthoplan.validation.measurement_models import (
    MeasurementTruthResult,
    MeasurementValue,
    result,
)
from orthoplan.validation.segmentation_compactness import score_compactness
from orthoplan.validation.segmentation_truth import (
    build_synthetic_arch,
    full_arch_truth,
    realistic_widths,
)

_ARCH = "maxillary"


def segmentation_crown_compactness() -> MeasurementTruthResult:
    """Gate per-tooth region compactness on the realistic synthetic arch."""

    case_id = "segmentation-crown-compactness"
    teeth = full_arch_truth(_ARCH)
    arch = build_synthetic_arch(
        teeth, sector_weights=realistic_widths(teeth), occlusal_flat=0.6, noise=0.15
    )
    segments = load_local_segmenter().segment(arch.vertices, arch=_ARCH)
    expected_count = len(default_arch_order(_ARCH))
    score = score_compactness(segments, expected_count=expected_count)

    # Floors just below the current heuristic baseline (mean ~0.50, min ~0.37). A
    # planar-slice regression that sprawls regions drops these; a learned backend
    # with crown-hugging boundaries should clear them with room to spare.
    min_mean_compactness = 0.45
    min_worst_compactness = 0.30
    expected: dict[str, MeasurementValue] = {
        "min_mean_compactness": min_mean_compactness,
        "min_worst_compactness": min_worst_compactness,
    }
    observed: dict[str, MeasurementValue] = {
        "segment_count": score.segment_count,
        "mean_compactness": score.mean_compactness,
        "min_compactness": score.min_compactness,
        "expected_crown_radius": score.expected_crown_radius,
    }

    failures: list[str] = []
    if score.mean_compactness < min_mean_compactness:
        failures.append(
            f"mean compactness {score.mean_compactness} below floor {min_mean_compactness}"
        )
    if score.min_compactness < min_worst_compactness:
        failures.append(
            f"worst-region compactness {score.min_compactness} below floor "
            f"{min_worst_compactness}"
        )
    return result(case_id, failures, expected=expected, observed=observed)
