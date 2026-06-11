from __future__ import annotations

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.evaluation.rules.contact_geometry import (
    ContactCandidate,
    staged_contact_candidates,
)
from orthoplan.model.assets import BoundingBox, MeshAsset
from orthoplan.model.plan import TreatmentPlan

_REFERENCE = (
    "Adjacent segmented-crown contact check using transformed crown bounds plus "
    "capped representative surface samples."
)
_GAP = (
    "Collision check uses segmented crown surface samples only. It does not evaluate "
    "roots, occlusion dynamics, material thickness, enamel biology, or biological response."
)
_QUESTION = "Should tooth positions, staging, IPR, or segmentation be reviewed for this contact?"


def evaluate_segmented_mesh_collisions(plan: TreatmentPlan) -> list[Finding]:
    bounds_by_tooth = _bounds_by_tooth(plan)
    if len(bounds_by_tooth) < 2:
        return []
    if not plan.scale_confirmed:
        return [_scale_unconfirmed_notice()]

    candidates = staged_contact_candidates(plan, bounds_by_tooth)
    return [
        _contact_finding(candidate)
        for candidate in sorted(candidates.values(), key=lambda item: (item.tooth_a, item.tooth_b))
    ]


def _bounds_by_tooth(plan: TreatmentPlan) -> dict[str, BoundingBox]:
    assets = _assets_by_id(plan)
    bounds_by_tooth: dict[str, BoundingBox] = {}
    for link in plan.tooth_meshes:
        asset = assets.get(link.mesh_asset_id)
        if asset and asset.bounds:
            bounds_by_tooth[link.tooth.value] = asset.bounds
    return bounds_by_tooth


def _contact_finding(candidate: ContactCandidate) -> Finding:
    detail = _sample_detail(candidate)
    return lint_finding(
        Finding(
            severity=FindingSeverity.WARNING,
            category=FindingCategory.MECHANICS,
            provenance=FindingProvenance.RULE,
            title=f"Teeth {candidate.tooth_a} and {candidate.tooth_b} interproximal contact estimated",
            message=(
                f"Teeth {candidate.tooth_a} and {candidate.tooth_b} have transformed adjacent "
                f"crown contact at stage {candidate.stage_index}. {detail} Estimated IPR "
                f"needed to separate the sampled crown geometry is {candidate.ipr_mm:.3f} mm."
            ),
            code="segmented-crown-sample-contact",
            data_gap=_GAP,
            clinician_question=_QUESTION,
            reference=_REFERENCE,
        )
    )


def _sample_detail(candidate: ContactCandidate) -> str:
    if candidate.sample_based:
        return (
            f"Minimum representative-surface distance is "
            f"{candidate.sample_distance_mm:.3f} mm after bbox prefilter."
        )
    return (
        "Representative surface samples are absent, so this falls back to the "
        f"axis-aligned bbox overlap depth of {candidate.bbox_overlap_mm:.3f} mm."
    )


def _scale_unconfirmed_notice() -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.NOTICE,
            category=FindingCategory.DATA_GAP,
            provenance=FindingProvenance.RULE,
            title="Crown collision check skipped: scan units unverified",
            message=(
                "Segmented crown bounds are present but scan units are unverified, so "
                "overlap depths cannot be compared in millimeters. Confirm scan units "
                "to enable the crown collision check."
            ),
            code="segmented-crown-collision-scale-unconfirmed",
            data_gap="Scan units are unverified; declared geometry scale cannot be trusted.",
            clinician_question="Have the scan units and scale been confirmed?",
        )
    )


def _assets_by_id(plan: TreatmentPlan) -> dict[str, MeshAsset]:
    assets = {asset.id: asset for asset in plan.mesh_assets}
    assets.update({scan.asset.id: scan.asset for scan in plan.scans})
    return assets
