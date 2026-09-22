"""Fail-closed numeric quality gate for STL-to-CBCT registrations.

``RegistrationTransform.is_acceptable`` checks that a human accepted a
registration AND that quality metrics were recorded - but not what the metrics
SAY. A registration accepted with a 5 mm RMSE would still unlock CBCT-derived
behavior. This gate adds the missing numeric judgement: deterministic
thresholds grade the recorded metrics into PASS / MARGINAL / FAIL, and every
CBCT-derived consumer (anatomy proposals, segmentation boundary priors, trusted
axis frames, root/bone checks) must consult the gate and stop on FAIL.

The thresholds are geometric review heuristics for clear-aligner-scale work:
PASS means sub-voxel agreement on a typical 0.2-0.4 mm CBCT; MARGINAL means the
registration may localize boundaries but should not be over-trusted (consumers
may use it with a caveat, but must not raise confidence on its evidence); FAIL
means the metrics contradict the acceptance. None of this is a clinical
acceptance criterion - a PASS never means the registration is clinically valid.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from orthoplan.model.registration import RegistrationQuality, RegistrationTransform

# RMSE between registered surfaces, in mm. Sub-half-voxel agreement passes;
# beyond one voxel the transform cannot be trusted to place tooth boundaries.
RMSE_PASS_MM = 0.5
RMSE_MARGINAL_MM = 1.0
# Fitness / inlier ratio of the correspondence set (0..1).
FIT_PASS = 0.8
FIT_MARGINAL = 0.5


class RegistrationGateVerdict(StrEnum):
    """Ordered worst-to-best so combining grades can take the minimum rank."""

    FAIL = "FAIL"
    MARGINAL = "MARGINAL"
    PASS = "PASS"


_RANK = {
    RegistrationGateVerdict.FAIL: 0,
    RegistrationGateVerdict.MARGINAL: 1,
    RegistrationGateVerdict.PASS: 2,
}


class RegistrationGateResult(BaseModel):
    """The gate's judgement of one registration, with per-metric reasons."""

    registration_id: str
    verdict: RegistrationGateVerdict
    reasons: list[str] = Field(default_factory=list)
    rmse_mm: float | None = None
    fitness: float | None = None
    inlier_ratio: float | None = None

    @property
    def open(self) -> bool:
        """Whether CBCT-derived consumers may proceed (PASS or MARGINAL)."""

        return self.verdict is not RegistrationGateVerdict.FAIL


def _grade_rmse(rmse_mm: float) -> tuple[RegistrationGateVerdict, str]:
    if rmse_mm <= RMSE_PASS_MM:
        return RegistrationGateVerdict.PASS, f"rmse {rmse_mm:.2f} mm <= {RMSE_PASS_MM} mm"
    if rmse_mm <= RMSE_MARGINAL_MM:
        return (
            RegistrationGateVerdict.MARGINAL,
            f"rmse {rmse_mm:.2f} mm is marginal (<= {RMSE_MARGINAL_MM} mm)",
        )
    return RegistrationGateVerdict.FAIL, f"rmse {rmse_mm:.2f} mm > {RMSE_MARGINAL_MM} mm"


def _grade_fit(value: float, label: str) -> tuple[RegistrationGateVerdict, str]:
    if value >= FIT_PASS:
        return RegistrationGateVerdict.PASS, f"{label} {value:.2f} >= {FIT_PASS}"
    if value >= FIT_MARGINAL:
        return RegistrationGateVerdict.MARGINAL, f"{label} {value:.2f} is marginal (>= {FIT_MARGINAL})"
    return RegistrationGateVerdict.FAIL, f"{label} {value:.2f} < {FIT_MARGINAL}"


def _grade_quality(quality: RegistrationQuality) -> tuple[RegistrationGateVerdict, list[str]]:
    grades: list[tuple[RegistrationGateVerdict, str]] = []
    if quality.rmse_mm is not None:
        grades.append(_grade_rmse(quality.rmse_mm))
    if quality.fitness is not None:
        grades.append(_grade_fit(quality.fitness, "fitness"))
    if quality.inlier_ratio is not None:
        grades.append(_grade_fit(quality.inlier_ratio, "inlier ratio"))
    if not grades:
        return (
            RegistrationGateVerdict.FAIL,
            ["quality metrics carry no usable values (rmse/fitness/inlier ratio all absent)"],
        )
    worst = min((verdict for verdict, _reason in grades), key=lambda v: _RANK[v])
    return worst, [reason for _verdict, reason in grades]


def gate_registration(registration: RegistrationTransform) -> RegistrationGateResult:
    """Grade one registration. Fail-closed: anything unverifiable is FAIL."""

    quality = registration.quality
    if not registration.accepted:
        verdict, reasons = RegistrationGateVerdict.FAIL, ["not accepted by a reviewer"]
    elif quality is None:
        verdict, reasons = RegistrationGateVerdict.FAIL, ["no quality metrics recorded"]
    else:
        verdict, reasons = _grade_quality(quality)
    return RegistrationGateResult(
        registration_id=registration.id,
        verdict=verdict,
        reasons=reasons,
        rmse_mm=quality.rmse_mm if quality else None,
        fitness=quality.fitness if quality else None,
        inlier_ratio=quality.inlier_ratio if quality else None,
    )


def gate_registrations(plan) -> list[RegistrationGateResult]:
    """Gate every registration on a plan (UI/report surface)."""

    return [gate_registration(reg) for reg in getattr(plan, "registrations", None) or []]


def best_gated_registration(
    plan,
) -> tuple[RegistrationTransform | None, RegistrationGateResult | None]:
    """The best non-FAIL registration (PASS preferred over MARGINAL), or ``(None, None)``.

    This is the single lookup CBCT-derived consumers should use: it never
    returns a registration whose recorded metrics contradict its acceptance.
    """

    best: tuple[RegistrationTransform, RegistrationGateResult] | None = None
    for registration in getattr(plan, "registrations", None) or []:
        result = gate_registration(registration)
        if not result.open:
            continue
        if best is None or _RANK[result.verdict] > _RANK[best[1].verdict]:
            best = (registration, result)
            if result.verdict is RegistrationGateVerdict.PASS:
                break
    if best is None:
        return None, None
    return best
