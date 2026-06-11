from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from orthoplan.model.assets import CaseRecord, MeshAsset, MeshProvenance, UploadedScan
from orthoplan.model.clinical import (
    Attachment,
    FixedTooth,
    InterproximalReduction,
    MovementAxis,
    MovementExclusion,
    PlannedSpacing,
)
from orthoplan.model.anatomy import DerivedAnatomy
from orthoplan.model.geometry import SCAN_FRAME, CoordinateFrame, ToothLocalFrame, Vec3
from orthoplan.model.identity import Arch, NumberingSystem, ToothId
from orthoplan.model.registration import RegistrationTransform
from orthoplan.model.settings import TreatmentSettings

CBCT_RECORD_KINDS = ("cbct", "dicom")


class ToothDelta(BaseModel):
    """A proposed tooth movement in explicit units within a named frame.

    ``arch`` is derived from the FDI tooth id, not stored, so the two can never
    contradict. Rotations (tip/torque/rotation) are authored values; whether
    they can be rendered depends on the plan coordinate frame (see geometry).
    """

    tooth: ToothId
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0
    translate_z_mm: float = 0.0
    rotate_tip_deg: float = 0.0
    rotate_torque_deg: float = 0.0
    rotate_rotation_deg: float = 0.0
    coordinate_frame: str = SCAN_FRAME.name
    source: Literal["manual", "imported", "model", "synthetic"] = "manual"
    # Reserved linkage to a per-tooth segmented mesh asset (populated in later phases).
    mesh_asset_id: str | None = None

    @property
    def arch(self) -> Arch:
        return self.tooth.arch

    def moved_axes(self) -> list[MovementAxis]:
        """Movement axes with a nonzero component, in canonical order.

        Shared by the staging optimizer and the clinical-control rules so both
        agree on what counts as movement on a given axis (drift between the two
        would mis-flag fixed-tooth / exclusion violations).
        """

        axes: list[MovementAxis] = []
        if self.translate_x_mm:
            axes.append("translate_x")
        if self.translate_y_mm:
            axes.append("translate_y")
        if self.translate_z_mm:
            axes.append("translate_z")
        if self.rotate_tip_deg:
            axes.append("tip")
        if self.rotate_torque_deg:
            axes.append("torque")
        if self.rotate_rotation_deg:
            axes.append("rotation")
        return axes


class Stage(BaseModel):
    index: int = Field(ge=0)
    deltas: list[ToothDelta] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("deltas")
    @classmethod
    def unique_teeth(cls, deltas: list[ToothDelta]) -> list[ToothDelta]:
        seen: set[str] = set()
        for delta in deltas:
            key = delta.tooth.value
            if key in seen:
                raise ValueError(f"duplicate tooth delta in stage: {key}")
            seen.add(key)
        return deltas


class DataAvailability(BaseModel):
    intraoral_scan: bool = True
    segmented_teeth: bool = False
    roots: bool = False
    cbct: bool = False
    periodontal_status: bool = False
    occlusion_scan: bool = False
    photos: bool = False
    radiographs: bool = False
    clinician_notes: bool = False


class SegmentedToothMesh(BaseModel):
    """Link a canonical tooth id to a mesh asset produced by segmentation.

    ``local_frame`` is an optional per-tooth frame (see ToothLocalFrame).
    Approximate PCA frames are metadata only; rotation rendering requires a
    trusted non-approximate frame.
    """

    tooth: ToothId
    mesh_asset_id: str
    source: MeshProvenance = MeshProvenance.MANUAL
    local_frame: ToothLocalFrame | None = None
    surface_sample_points: list[Vec3] = Field(default_factory=list, max_length=64)
    # A link is ``reviewed`` once a human has accepted/corrected the proposed
    # segmentation. Real per-tooth vertices are exported ONLY for reviewed links;
    # auto-draft links (reviewed=False) fall back to a labeled schematic proxy.
    reviewed: bool = False
    notes: str | None = None

    @field_validator("surface_sample_points")
    @classmethod
    def cap_surface_samples(cls, points: list[Vec3]) -> list[Vec3]:
        if len(points) > 64:
            raise ValueError("surface_sample_points is capped at 64 points per tooth")
        return points


class TreatmentPlan(BaseModel):
    id: str
    title: str = "Untitled plan"
    numbering_system: NumberingSystem = "FDI"
    coordinate_frame: CoordinateFrame = SCAN_FRAME
    data: DataAvailability = Field(default_factory=DataAvailability)
    settings: TreatmentSettings = Field(default_factory=TreatmentSettings)
    scans: list[UploadedScan] = Field(default_factory=list)
    case_records: list[CaseRecord] = Field(default_factory=list)
    mesh_assets: list[MeshAsset] = Field(default_factory=list)
    tooth_meshes: list[SegmentedToothMesh] = Field(default_factory=list)
    registrations: list[RegistrationTransform] = Field(default_factory=list)
    derived_anatomy: DerivedAnatomy | None = None
    fixed_teeth: list[FixedTooth] = Field(default_factory=list)
    movement_exclusions: list[MovementExclusion] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    interproximal_reductions: list[InterproximalReduction] = Field(default_factory=list)
    planned_spacing: list[PlannedSpacing] = Field(default_factory=list)
    stages: list[Stage] = Field(default_factory=list)

    @property
    def scale_confirmed(self) -> bool:
        """True when cap evaluation may run: no scans, or all scan units confirmed."""

        return all(scan.units_confirmed for scan in self.scans)

    @property
    def segmented_tooth_values(self) -> set[str]:
        return {link.tooth.value for link in self.tooth_meshes}

    @property
    def asset_ids(self) -> set[str]:
        return {scan.asset.id for scan in self.scans} | {asset.id for asset in self.mesh_assets}

    @field_validator("stages")
    @classmethod
    def stage_indexes_are_contiguous(cls, stages: list[Stage]) -> list[Stage]:
        indexes = [stage.index for stage in stages]
        if indexes != list(range(len(stages))):
            raise ValueError("stage indexes must be contiguous and start at 0")
        return stages

    @model_validator(mode="after")
    def deltas_match_plan_identity(self) -> TreatmentPlan:
        frame_name = self.coordinate_frame.name

        # Asset ids must be unique across scans and mesh assets; otherwise a
        # segmented-mesh link would resolve ambiguously to two different assets.
        all_asset_ids = [scan.asset.id for scan in self.scans] + [a.id for a in self.mesh_assets]
        if len(all_asset_ids) != len(set(all_asset_ids)):
            raise ValueError("duplicate mesh asset id across scans/mesh_assets")
        asset_ids = set(all_asset_ids)

        record_ids = [record.id for record in self.case_records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("duplicate case record id")

        self._validate_registrations(asset_ids)
        self._validate_derived_anatomy(asset_ids)

        # Build the canonical tooth -> mesh map while rejecting duplicate links.
        tooth_to_mesh: dict[str, str] = {}
        for link in self.tooth_meshes:
            if link.tooth.value in tooth_to_mesh:
                raise ValueError(f"duplicate segmented tooth mesh: {link.tooth.value}")
            if link.mesh_asset_id not in asset_ids:
                raise ValueError(
                    "segmented tooth mesh references unknown mesh asset "
                    f"{link.mesh_asset_id!r}"
                )
            tooth_to_mesh[link.tooth.value] = link.mesh_asset_id

        for stage in self.stages:
            for delta in stage.deltas:
                if delta.tooth.system != self.numbering_system:
                    raise ValueError(
                        "mixed numbering systems are rejected: plan uses "
                        f"{self.numbering_system}, delta uses {delta.tooth.system}"
                    )
                if delta.coordinate_frame != frame_name:
                    raise ValueError(
                        "mixed coordinate frames are rejected: plan frame is "
                        f"{frame_name!r}, delta frame is {delta.coordinate_frame!r}"
                    )
                # A delta may only reference the mesh segmented to its OWN tooth,
                # so a delta can never move another tooth's geometry.
                if delta.mesh_asset_id and tooth_to_mesh.get(delta.tooth.value) != delta.mesh_asset_id:
                    raise ValueError(
                        "tooth delta references unknown segmented mesh asset "
                        f"{delta.mesh_asset_id!r} for tooth {delta.tooth.value}"
                    )
        return self

    def _validate_registrations(self, asset_ids: set[str]) -> None:
        """Registration transforms must reference a real mesh asset and CBCT record.

        Keeps an accepted registration from ever pointing at geometry or a volume
        that is not in the plan.
        """

        cbct_record_ids = {
            record.id for record in self.case_records if record.kind in CBCT_RECORD_KINDS
        }
        seen_reg_ids: set[str] = set()
        for reg in self.registrations:
            if reg.id in seen_reg_ids:
                raise ValueError(f"duplicate registration id: {reg.id}")
            seen_reg_ids.add(reg.id)
            if reg.source_stl_asset_id not in asset_ids:
                raise ValueError(
                    f"registration references unknown source mesh asset {reg.source_stl_asset_id!r}"
                )
            if reg.target_cbct_record_id not in cbct_record_ids:
                raise ValueError(
                    "registration references unknown CBCT/DICOM record "
                    f"{reg.target_cbct_record_id!r}"
                )

    def _validate_derived_anatomy(self, asset_ids: set[str]) -> None:
        """Every derived-anatomy object must trace to a real CBCT record and registration.

        Provenance integrity is what makes 'reviewed' meaningful - a trusted root
        or axis can never reference a volume, registration, or mesh not in the plan.
        """

        if self.derived_anatomy is None:
            return
        cbct_record_ids = {
            record.id for record in self.case_records if record.kind in CBCT_RECORD_KINDS
        }
        registration_ids = {reg.id for reg in self.registrations}
        for obj in self.derived_anatomy.all_objects():
            if obj.source_cbct_record_id not in cbct_record_ids:
                raise ValueError(
                    f"derived anatomy references unknown CBCT record {obj.source_cbct_record_id!r}"
                )
            if obj.registration_id not in registration_ids:
                raise ValueError(
                    f"derived anatomy references unknown registration {obj.registration_id!r}"
                )
            mesh_id = getattr(obj, "mesh_asset_id", None)
            if mesh_id is not None and mesh_id not in asset_ids:
                raise ValueError(
                    f"derived anatomy references unknown mesh asset {mesh_id!r}"
                )
