"""CBCT boundary priors for surface segmentation (Step 2 of the fidelity path).

Teeth that merge into one surface blob on an STL are physically separated in a
CBCT volume (periodontal ligament space, density contrast). When a plan carries
TRUSTED (human-reviewed, in-field) CBCT-derived root anatomy behind a
registration whose numeric quality gate is open, this module turns that anatomy
into scan-space interproximal boundary priors: the midpoint between each
adjacent pair of per-tooth root positions, mapped from CBCT space into scan
space through the inverse registration transform.

Fail-closed at every step: no gated registration, no trusted anatomy, fewer
than two teeth in the arch, or a non-invertible registration matrix all yield
``None`` (the segmenter then runs surface-only, exactly as before). A MARGINAL
gate may bias cut placement but never raises confidence; only PASS allows the
cross-modal confidence boost (see ``hybrid._cross_modal_confidence``).
"""

from __future__ import annotations

from dataclasses import dataclass

from orthoplan.arch_contract import arch_from_tooth_value
from orthoplan.model.anatomy import DerivedAnatomy
from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Matrix4, Vec3, apply_affine, invert_affine
from orthoplan.model.registration_gate import (
    RegistrationGateResult,
    RegistrationGateVerdict,
    gate_registration,
)
from orthoplan.segmentation.heuristic import default_arch_order


@dataclass(frozen=True)
class CbctBoundaryPriors:
    """Scan-space interproximal priors for one arch, with their gate provenance."""

    arch: ArchName
    points: list[Vec3]
    tooth_pairs: list[tuple[str, str]]
    registration_ids: list[str]
    gate_verdicts: list[str]
    allow_confidence_boost: bool


def boundary_priors_for_arch(plan, arch: ArchName) -> CbctBoundaryPriors | None:
    """Build interproximal boundary priors for ``arch`` from trusted anatomy."""

    anatomy: DerivedAnatomy | None = getattr(plan, "derived_anatomy", None)
    if anatomy is None:
        return None
    gates = _open_gates(plan)
    if not gates:
        return None
    tooth_points = _trusted_tooth_points(plan, anatomy, arch, gates)
    if len(tooth_points) < 2:
        return None

    ordered = [tooth for tooth in default_arch_order(arch) if tooth in tooth_points]
    points: list[Vec3] = []
    pairs: list[tuple[str, str]] = []
    for tooth_a, tooth_b in zip(ordered, ordered[1:]):
        a, b = tooth_points[tooth_a], tooth_points[tooth_b]
        points.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2))
        pairs.append((tooth_a, tooth_b))
    if not points:
        return None
    used_gates = sorted({gates[rid].registration_id for rid in gates}, key=str)
    return CbctBoundaryPriors(
        arch=arch,
        points=points,
        tooth_pairs=pairs,
        registration_ids=used_gates,
        gate_verdicts=[gates[rid].verdict.value for rid in sorted(gates)],
        allow_confidence_boost=all(
            gates[rid].verdict is RegistrationGateVerdict.PASS for rid in gates
        ),
    )


def _open_gates(plan) -> dict[str, RegistrationGateResult]:
    """Gate results for every registration whose numeric gate is open."""

    out: dict[str, RegistrationGateResult] = {}
    for registration in getattr(plan, "registrations", None) or []:
        result = gate_registration(registration)
        if result.open:
            out[registration.id] = result
    return out


def _trusted_tooth_points(
    plan, anatomy: DerivedAnatomy, arch: ArchName, gates: dict[str, RegistrationGateResult]
) -> dict[str, Vec3]:
    """One scan-space point per trusted tooth in ``arch`` (root centroid or axis origin)."""

    inverses = _inverse_registration_matrices(plan, gates)
    points: dict[str, Vec3] = {}
    for root in anatomy.roots:
        tooth = root.tooth.value
        if not root.trusted or not root.centerline or arch_from_tooth_value(tooth) != arch:
            continue
        inverse = inverses.get(root.registration_id)
        if inverse is None:
            continue
        points[tooth] = apply_affine(inverse, _mean3(root.centerline))
    for axis in anatomy.tooth_axes:
        tooth = axis.tooth.value
        if tooth in points or not axis.trusted or arch_from_tooth_value(tooth) != arch:
            continue
        inverse = inverses.get(axis.registration_id)
        if inverse is None:
            continue
        points[tooth] = apply_affine(inverse, axis.origin_mm)
    return points


def _inverse_registration_matrices(
    plan, gates: dict[str, RegistrationGateResult]
) -> dict[str, Matrix4]:
    """Inverse (CBCT -> scan space) matrix per gated registration id.

    The recorded matrix maps the STL source into the CBCT target, so anatomy
    points (CBCT space) come back through the inverse. A singular matrix yields
    no entry - the anatomy behind it is skipped rather than misplaced.
    """

    out: dict[str, Matrix4] = {}
    for registration in getattr(plan, "registrations", None) or []:
        if registration.id not in gates:
            continue
        inverse = invert_affine(registration.matrix)
        if inverse is not None:
            out[registration.id] = inverse
    return out


def _mean3(points: list[Vec3]) -> Vec3:
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
        sum(p[2] for p in points) / len(points),
    )


def priors_from_plan_payload(raw: object) -> tuple[dict[ArchName, CbctBoundaryPriors], str]:
    """CBCT boundary priors per arch from a caller's optional raw plan dict.

    The plan is optional and the prior path is strictly additive, so any
    problem (no plan, invalid plan, no gated registration, no trusted anatomy)
    degrades to surface-only segmentation with a stated reason - it never
    fails the request.
    """

    from orthoplan.model.plan import TreatmentPlan

    if not isinstance(raw, dict):
        return {}, "no plan supplied"
    try:
        plan = TreatmentPlan.model_validate(raw)
    except Exception:  # noqa: BLE001 - priors are additive; invalid plan = no priors
        return {}, "plan did not validate"
    priors: dict[ArchName, CbctBoundaryPriors] = {}
    for arch in ("maxillary", "mandibular"):
        prior = boundary_priors_for_arch(plan, arch)
        if prior is not None:
            priors[arch] = prior
    if not priors:
        return {}, "no gated registration with trusted per-tooth anatomy"
    return priors, "priors available"


def prior_response_block(
    priors_by_arch: dict[ArchName, CbctBoundaryPriors],
    cross_modal_by_arch: dict,
    status: str,
) -> dict:
    """The ``cbct_prior`` block of the /api/segment response."""

    arches: dict[str, dict] = {}
    for arch, prior in sorted(priors_by_arch.items()):
        report = cross_modal_by_arch.get(arch)
        arches[arch] = {
            "boundary_count": len(prior.points),
            "gate_verdicts": prior.gate_verdicts,
            "confidence_boost": prior.allow_confidence_boost,
            "mean_agreement": report.mean_agreement if report else None,
        }
    return {"used": bool(arches), "status": status, "arches": arches}
