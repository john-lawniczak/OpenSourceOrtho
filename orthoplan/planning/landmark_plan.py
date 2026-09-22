"""Assemble enriched plan inputs from per-tooth crown landmarks.

Turns ``ArchLandmarks`` into the pieces a clinically-coherent plan needs:

- per-tooth movement **targets** (deviation onto the fitted arch),
- **IPR** records that budget the crowding space,
- **attachments** on teeth that actually move (so movement is not authored
  without an auxiliary), and
- approximate per-tooth **collision bounds** (synthetic boxes at the landmark,
  sized from the crown-width table) so the segmented-collision rule is no longer
  vacuous.

Everything is geometric and labeled approximate; it never infers roots/bone.
Kept separate from ``generate.py`` so that module stays small.
"""

from __future__ import annotations

from math import hypot

from pydantic import BaseModel, Field

from orthoplan.model.assets import BoundingBox, MeshAsset, MeshProvenance, MeshUnits
from orthoplan.model.clinical import Attachment, InterproximalReduction
from orthoplan.model.landmarks import ArchLandmarks
from orthoplan.model.plan import SegmentedToothMesh, ToothDelta, ToothId
from orthoplan.planning.arch_analysis import analyze_arch, crown_width

# Author an attachment when a tooth's planned movement exceeds this magnitude.
_ATTACHMENT_THRESHOLD_MM = 0.3
_CROWN_HEIGHT_MM = 7.0
# Box footprint is a fraction of the mesiodistal width so adjacent approximate
# boxes do not overlap purely from rounding (collisions then mean real contact).
_BOX_FOOTPRINT = 0.85


class LandmarkPlanInputs(BaseModel):
    targets: list[ToothDelta] = Field(default_factory=list)
    iprs: list[InterproximalReduction] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    mesh_assets: list[MeshAsset] = Field(default_factory=list)
    tooth_meshes: list[SegmentedToothMesh] = Field(default_factory=list)
    discrepancy_mm: float = 0.0
    residual_mm: float = 0.0
    warnings: list[str] = Field(default_factory=list)


def _crown_bounds(value: str, x: float, y: float) -> BoundingBox:
    half_md = crown_width(value) * _BOX_FOOTPRINT / 2
    half_bl = crown_width(value) * _BOX_FOOTPRINT * 0.4
    return BoundingBox(
        min_xyz=(x - half_md, y - half_bl, 0.0),
        max_xyz=(x + half_md, y + half_bl, _CROWN_HEIGHT_MM),
    )


def _add_arch(out: LandmarkPlanInputs, arch_landmarks: list, frame_name: str) -> tuple[float, float]:
    centroids = {lm.tooth.value: (lm.x_mm, lm.y_mm) for lm in arch_landmarks}
    analysis = analyze_arch(centroids)

    for value, (dx, dy) in analysis.corrections.items():
        if dx == 0.0 and dy == 0.0:
            continue
        tooth = ToothId(value=value)
        out.targets.append(ToothDelta(tooth=tooth, translate_x_mm=dx, translate_y_mm=dy,
                                      coordinate_frame=frame_name, source="model"))
        if hypot(dx, dy) >= _ATTACHMENT_THRESHOLD_MM:
            out.attachments.append(Attachment(tooth=tooth, type="optimized", surface="buccal",
                                              purpose="landmark-derived movement"))

    for item in analysis.ipr_plan:
        out.iprs.append(InterproximalReduction(
            tooth_a=ToothId(value=item.tooth_a), tooth_b=ToothId(value=item.tooth_b),
            amount_mm=item.amount_mm, stage_index=0, source="model",
            notes="landmark-derived space analysis"))

    for lm in arch_landmarks:
        asset_id = f"lm-{lm.tooth.value}"
        out.mesh_assets.append(MeshAsset(
            id=asset_id, format="synthetic-box", provenance=MeshProvenance.SYNTHETIC,
            units=MeshUnits.MM, vertex_count=0, face_count=0,
            bounds=_crown_bounds(lm.tooth.value, lm.x_mm, lm.y_mm)))
        out.tooth_meshes.append(SegmentedToothMesh(
            tooth=lm.tooth, mesh_asset_id=asset_id, source=MeshProvenance.SYNTHETIC,
            notes="approximate crown box from landmark + crown-width table"))

    return analysis.discrepancy_mm, analysis.residual_mm


def build_landmark_inputs(landmarks: ArchLandmarks, frame_name: str) -> LandmarkPlanInputs:
    out = LandmarkPlanInputs()
    discrepancy = 0.0
    residual = 0.0
    for arch_landmarks in landmarks.by_arch().values():
        d, r = _add_arch(out, arch_landmarks, frame_name)
        discrepancy += d
        residual += r

    out.discrepancy_mm = round(discrepancy, 3)
    out.residual_mm = round(residual, 3)
    if landmarks.approximate:
        out.warnings.append(
            "Targets are derived from APPROXIMATE crown landmarks; refine to precise "
            "landmarks (or segmented meshes) for a higher-fidelity plan."
        )
    if out.residual_mm > 0:
        out.warnings.append(
            f"{out.residual_mm} mm of crowding exceeds the IPR budget (cap "
            "0.5 mm/contact); expansion or extraction is a clinician decision, not generated here."
        )
    return out
