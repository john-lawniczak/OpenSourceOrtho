"""Deterministic mesh-validation findings (Phase 3).

Turns the observational `MeshQualityReport` and bounding-box sanity check into
lint-passed `Finding`s so malformed-mesh and scale-ambiguity warnings flow
through the same engine, api, and UI as every other finding.

These are NOTICE-level, observational, and never imply the mesh is unusable -
they surface what inspection saw so a reviewer or technician can decide.
"""

from __future__ import annotations

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)
from orthoplan.model.assets import MeshAsset, bounding_box_sanity
from orthoplan.model.plan import TreatmentPlan


def evaluate_mesh_quality(plan: TreatmentPlan) -> list[Finding]:
    # Per-tooth crown meshes are not whole arches, so the arch-scale sanity range
    # (30-120 mm) must not apply to them - otherwise every segmented crown is
    # mis-flagged as "implausible scale".
    crown_ids = {link.mesh_asset_id for link in plan.tooth_meshes}
    findings: list[Finding] = []
    for asset in _plan_assets(plan):
        findings.extend(_asset_findings(asset, is_crown=asset.id in crown_ids))
    return findings


def _plan_assets(plan: TreatmentPlan) -> list[MeshAsset]:
    return [scan.asset for scan in plan.scans] + list(plan.mesh_assets)


def _asset_findings(asset: MeshAsset, *, is_crown: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    report = asset.quality

    if report and report.degenerate_faces:
        findings.append(
            _notice(
                FindingCategory.CONSISTENCY,
                f"Mesh {asset.id} has degenerate triangles",
                f"Inspection found {report.degenerate_faces} zero-area triangle(s) in mesh "
                f"{asset.id}. Degenerate faces can distort surface rendering and measurements.",
            )
        )

    if report and report.watertight is False:
        findings.append(
            _notice(
                FindingCategory.CONSISTENCY,
                f"Mesh {asset.id} is not watertight",
                f"Mesh {asset.id} was reported as not watertight. Open surfaces are expected for "
                "crown-only intraoral scans, but confirm the mesh is complete for the intended use.",
            )
        )

    if report and report.winding_consistent is False:
        findings.append(
            _notice(
                FindingCategory.CONSISTENCY,
                f"Mesh {asset.id} has inconsistent winding",
                f"Mesh {asset.id} has inconsistent face winding, which can flip normals and affect "
                "shading or downstream geometry operations.",
            )
        )

    # Scale ambiguity for unverified units is already reported by the movement-cap
    # rule; here we only flag confirmed-but-implausible scale (arch scans only -
    # per-tooth crowns are legitimately far smaller than an arch).
    if asset.units_confirmed and not is_crown:
        note = bounding_box_sanity(asset)
        if note:
            findings.append(
                _notice(FindingCategory.DATA_GAP, f"Mesh {asset.id} scale looks implausible", note)
            )

    return findings


def _notice(category: FindingCategory, title: str, message: str) -> Finding:
    return lint_finding(
        Finding(
            severity=FindingSeverity.NOTICE,
            category=category,
            provenance=FindingProvenance.RULE,
            title=title,
            message=message,
        )
    )
