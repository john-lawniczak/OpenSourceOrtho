from __future__ import annotations

from orthoplan.arch_contract import arch_from_tooth_value
from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model.assets import BoundingBox, MeshAsset
from orthoplan.model.plan import TreatmentPlan
from orthoplan.viz.progress import build_stage_progress_frames

_REFERENCE = "Axis-aligned segmented crown bounding-box overlap check."
_GAP = (
    "Collision check uses segmented crown mesh bounds only. It does not evaluate "
    "roots, occlusion dynamics, material thickness, or biological response."
)
_QUESTION = "Should tooth positions, staging, IPR, or segmentation be reviewed for this contact?"


def evaluate_segmented_mesh_collisions(plan: TreatmentPlan) -> list[Finding]:
    assets = _assets_by_id(plan)
    bounds_by_tooth: dict[str, BoundingBox] = {}
    for link in plan.tooth_meshes:
        asset = assets.get(link.mesh_asset_id)
        if asset and asset.bounds:
            bounds_by_tooth[link.tooth.value] = asset.bounds
    if len(bounds_by_tooth) < 2:
        return []

    # Collect the worst (deepest) overlap per tooth pair across all stages so a
    # contact that persists through many stages is reported once - keyed by the
    # stage where it is most severe - instead of flooding the findings list with
    # one near-identical entry per stage.
    worst_by_pair: dict[tuple[str, str], tuple[int, float]] = {}
    for frame in build_stage_progress_frames(plan):
        moved = dict(bounds_by_tooth)
        for pose in frame.poses:
            if pose.tooth.value in bounds_by_tooth:
                moved[pose.tooth.value] = _translate_bounds(bounds_by_tooth[pose.tooth.value], pose)
        teeth = sorted(moved)
        for index, tooth_a in enumerate(teeth):
            for tooth_b in teeth[index + 1 :]:
                # Opposing arches share the occlusal x/y plane and are not
                # collision partners; only compare teeth within the same arch.
                if _arch_of(tooth_a) != _arch_of(tooth_b):
                    continue
                overlap = _overlap_depth(moved[tooth_a], moved[tooth_b])
                if overlap <= 0:
                    continue
                pair = (tooth_a, tooth_b)
                current = worst_by_pair.get(pair)
                if current is None or overlap > current[1]:
                    worst_by_pair[pair] = (frame.stage_index, overlap)

    findings: list[Finding] = []
    for (tooth_a, tooth_b), (stage_index, overlap) in sorted(worst_by_pair.items()):
        findings.append(
            lint_finding(
                Finding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.MECHANICS,
                    provenance=FindingProvenance.RULE,
                    title=f"Teeth {tooth_a} and {tooth_b} segmented crown bounds overlap",
                    message=(
                        f"Teeth {tooth_a} and {tooth_b} have overlapping transformed "
                        f"axis-aligned crown bounds, deepest at stage {stage_index} by "
                        f"approximately {overlap:.3f} mm on the shallowest overlapping axis."
                    ),
                    code="segmented-crown-bounds-overlap",
                    data_gap=_GAP,
                    clinician_question=_QUESTION,
                    reference=_REFERENCE,
                )
            )
        )
    return findings


def _arch_of(tooth_value: str) -> str:
    return arch_from_tooth_value(tooth_value)


def _assets_by_id(plan: TreatmentPlan) -> dict[str, MeshAsset]:
    assets = {asset.id: asset for asset in plan.mesh_assets}
    assets.update({scan.asset.id: scan.asset for scan in plan.scans})
    return assets


def _translate_bounds(bounds: BoundingBox, pose) -> BoundingBox:
    delta = (pose.translate_x_mm, pose.translate_y_mm, pose.translate_z_mm)
    return BoundingBox(
        min_xyz=tuple(bounds.min_xyz[i] + delta[i] for i in range(3)),  # type: ignore[return-value]
        max_xyz=tuple(bounds.max_xyz[i] + delta[i] for i in range(3)),  # type: ignore[return-value]
    )


def _overlap_depth(a: BoundingBox, b: BoundingBox) -> float:
    depths = []
    for axis in range(3):
        depth = min(a.max_xyz[axis], b.max_xyz[axis]) - max(a.min_xyz[axis], b.min_xyz[axis])
        if depth <= 0:
            return 0.0
        depths.append(depth)
    return min(depths)
