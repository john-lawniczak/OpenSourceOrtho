"""Prior-score blending and cross-modal confidence for the hybrid segmenter.

The hybrid segmenter scores candidate cut positions from surface signals alone.
When CBCT boundary priors exist (see ``cbct_prior``), these helpers bias the
cut placement toward the volume-indicated embrasures and turn cut/prior
agreement into a MEASURED per-tooth confidence calibration. Pure list math, no
dependencies, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

# A prior adds a Gaussian score bump; the surface signal keeps voting, so a
# misregistered prior cannot silently drag a cut onto smooth enamel.
_PRIOR_WEIGHT = 0.45
_PRIOR_SIGMA_BUCKETS = 3.6  # 0.45 of one tooth at 8 buckets/tooth
# A placed cut within half a tooth of a prior counts as the two modalities
# agreeing on that boundary.
_AGREEMENT_TOLERANCE_BUCKETS = 4.0
# Agreement-calibrated confidence: disagreement always lowers (x0.8 floor);
# raising above the surface-only score requires a PASS registration gate
# (``boost_applied``) and stays capped below certainty.
_CROSS_MODAL_FLOOR = 0.8
_CROSS_MODAL_GAIN = 0.35
MAX_CONFIDENCE_CROSS_MODAL = 0.93


@dataclass(frozen=True)
class CrossModalReport:
    """How the placed cuts compare to the CBCT boundary priors."""

    prior_buckets: tuple[int, ...]
    cut_agreements: tuple[float, ...]
    mean_agreement: float
    boost_applied: bool


def blend_prior_scores(scores: list[float], prior_buckets: list[int]) -> list[float]:
    """Add a Gaussian score bump around each CBCT boundary prior."""

    out = list(scores)
    for prior in prior_buckets:
        for index in range(len(out)):
            distance = index - prior
            out[index] += _PRIOR_WEIGHT * exp(
                -(distance * distance) / (2 * _PRIOR_SIGMA_BUCKETS * _PRIOR_SIGMA_BUCKETS)
            )
    return out


def cross_modal_report(
    boundary_buckets: list[int], prior_buckets: list[int], boost: bool
) -> CrossModalReport | None:
    """Per-cut agreement between the placed surface cuts and the CBCT priors."""

    if not prior_buckets:
        return None
    agreements = []
    for cut in boundary_buckets:
        nearest = min(abs(cut - prior) for prior in prior_buckets)
        agreements.append(max(0.0, 1.0 - nearest / _AGREEMENT_TOLERANCE_BUCKETS))
    mean = sum(agreements) / len(agreements) if agreements else 0.0
    return CrossModalReport(
        prior_buckets=tuple(prior_buckets),
        cut_agreements=tuple(round(a, 3) for a in agreements),
        mean_agreement=round(mean, 3),
        boost_applied=boost,
    )


def cross_modal_confidence(confidence: float, index: int, report: CrossModalReport) -> float:
    """Calibrate a tooth's confidence by its bounding cuts' cross-modal agreement.

    Agreement is MEASURED (surface cut vs volume prior), so confidence becomes a
    computed quantity: disagreement always lowers it; raising it above the
    surface-only score requires a PASS registration gate (``boost_applied``) and
    stays capped below certainty.
    """

    agreements = report.cut_agreements
    left = agreements[index - 1] if index > 0 else 1.0
    right = agreements[index] if index < len(agreements) else 1.0
    multiplier = _CROSS_MODAL_FLOOR + _CROSS_MODAL_GAIN * ((left + right) / 2)
    if not report.boost_applied:
        multiplier = min(1.0, multiplier)
    return min(MAX_CONFIDENCE_CROSS_MODAL, confidence * multiplier)
