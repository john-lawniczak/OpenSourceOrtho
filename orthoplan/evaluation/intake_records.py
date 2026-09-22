"""Surface and bite evidence from plan metadata; no filesystem or UI dependencies."""
from __future__ import annotations

import math
from collections import Counter

from orthoplan.model.assets import MeshUnits, bounding_box_sanity
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.readiness import ReadinessItem


def surface_records(plan: TreatmentPlan) -> list[ReadinessItem]:
    items = []
    arches = Counter(scan.arch for scan in plan.scans if scan.arch)
    for arch, label in (("maxillary", "Upper arch"), ("mandibular", "Lower arch")):
        count = arches[arch]
        items.append(ReadinessItem(
            id=f"arch:{arch}", label=label, scope="surface",
            state="missing" if not count else "needs_review" if count > 1 else "present",
            detail=(f"{count} scan record(s) labeled {arch}. Multiple records need identity review."
                    if count > 1 else f"{count} scan record(s) labeled {arch}."),
            action="label_arch" if count else "upload_scans",
        ))
    for scan in plan.scans:
        issues = []
        action = "upload_scans"
        if scan.arch is None:
            issues.append("Arch identity is unlabeled.")
            action = "label_arch"
        if not scan.asset.face_count or not scan.asset.vertex_count:
            issues.append("No mesh facets or vertices recorded.")
        if scan.asset.bounds is None:
            issues.append("Geometry bounds are unavailable.")
        elif not all(math.isfinite(v) and v >= 0 for v in scan.asset.bounds.size):
            issues.append("Geometry bounds are invalid.")
        if scan.asset.units != MeshUnits.MM:
            issues.append("Confirm or convert scan coordinates to millimeters before use.")
            action = "confirm_units"
        elif note := bounding_box_sanity(scan.asset):
            issues.append(note)
            action = "confirm_units"
        quality = scan.asset.quality
        if quality is None:
            issues.append("Mesh quality has not been inspected.")
        elif quality.degenerate_faces or quality.winding_consistent is False:
            issues.append("Mesh inspection recorded degeneracy or inconsistent winding.")
        items.append(ReadinessItem(
            id=f"scan:{scan.asset.id}", asset_id=scan.asset.id,
            label=f"Scan {scan.asset.id}", scope="surface",
            state="needs_review" if issues else "present",
            detail=" ".join(issues) or "Labeled millimeter scan metadata with inspected bounds.",
            action=action if issues else None,
        ))
    return items


def segmentation_records(plan: TreatmentPlan) -> list[ReadinessItem]:
    links = plan.tooth_meshes
    reviewed = {link.tooth.value for link in links if link.reviewed}
    moving = {delta.tooth.value for stage in plan.stages for delta in stage.deltas
              if delta.moved_axes()}
    missing = sorted(moving - reviewed)
    count = len(reviewed)
    detail = f"{count} of {len(links)} linked tooth mesh(es) explicitly reviewed."
    if missing:
        detail += f" Moving teeth without reviewed meshes: {', '.join(missing)}."
    return [
        ReadinessItem(
            id="segmentation", label="Per-tooth segmentation", scope="surface",
            state="missing" if not links else (
                "needs_review" if missing or count != len(links) else "present"),
            detail=detail, action="review_segmentation",
        ),
        ReadinessItem(
            id="segmentation_quality", label="Segmentation quality evidence", scope="surface",
            state="not_assessed", action="review_segmentation",
            detail="Plan links record human review, but do not persist a segmentation quality-gate report.",
        ),
        ReadinessItem(
            id="bite", label="Bite relationship", scope="bite", action="review_bite",
            state="needs_review" if plan.data.occlusion_scan else "missing",
            detail=("Bite availability is declared; this plan has no persisted bite-registration evidence."
                    if plan.data.occlusion_scan else "No bite relationship is declared."),
        ),
    ]
