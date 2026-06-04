from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from orthoplan.model.assets import MeshAsset, MeshProvenance, UploadedScan
from orthoplan.model.geometry import SCAN_FRAME, CoordinateFrame
from orthoplan.model.settings import TreatmentSettings


class Arch(StrEnum):
    MAXILLARY = "maxillary"
    MANDIBULAR = "mandibular"


# Phase 1 uses canonical internal FDI identity. Display conversion to Universal
# or Palmer is deferred; mixed numbering is rejected rather than normalized.
NumberingSystem = Literal["FDI"]

# FDI quadrant -> arch. Permanent (1-4) and primary (5-8) quadrants supported.
_MAXILLARY_QUADRANTS = {"1", "2", "5", "6"}
_MANDIBULAR_QUADRANTS = {"3", "4", "7", "8"}


class ToothId(BaseModel):
    """Canonical FDI tooth identity (two-digit notation, e.g. ``11``)."""

    model_config = ConfigDict(frozen=True)

    system: NumberingSystem = "FDI"
    value: str = Field(min_length=2, max_length=2)

    @field_validator("value")
    @classmethod
    def valid_fdi_value(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError(f"FDI tooth id must be two digits, got {value!r}")
        quadrant, tooth = value[0], value[1]
        if quadrant not in (_MAXILLARY_QUADRANTS | _MANDIBULAR_QUADRANTS):
            raise ValueError(f"FDI quadrant must be 1-8, got {quadrant!r} in {value!r}")
        if tooth not in {"1", "2", "3", "4", "5", "6", "7", "8"}:
            raise ValueError(f"FDI tooth position must be 1-8, got {tooth!r} in {value!r}")
        return value

    @property
    def quadrant(self) -> str:
        return self.value[0]

    @property
    def arch(self) -> Arch:
        return Arch.MAXILLARY if self.quadrant in _MAXILLARY_QUADRANTS else Arch.MANDIBULAR


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
    """Link a canonical tooth id to a mesh asset produced by segmentation."""

    tooth: ToothId
    mesh_asset_id: str
    source: MeshProvenance = MeshProvenance.MANUAL
    notes: str | None = None


class TreatmentPlan(BaseModel):
    id: str
    title: str = "Untitled plan"
    numbering_system: NumberingSystem = "FDI"
    coordinate_frame: CoordinateFrame = SCAN_FRAME
    data: DataAvailability = Field(default_factory=DataAvailability)
    settings: TreatmentSettings = Field(default_factory=TreatmentSettings)
    scans: list[UploadedScan] = Field(default_factory=list)
    mesh_assets: list[MeshAsset] = Field(default_factory=list)
    tooth_meshes: list[SegmentedToothMesh] = Field(default_factory=list)
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
        seen_links: set[str] = set()
        asset_ids = self.asset_ids
        for link in self.tooth_meshes:
            if link.tooth.value in seen_links:
                raise ValueError(f"duplicate segmented tooth mesh: {link.tooth.value}")
            if link.mesh_asset_id not in asset_ids:
                raise ValueError(
                    "segmented tooth mesh references unknown mesh asset "
                    f"{link.mesh_asset_id!r}"
                )
            seen_links.add(link.tooth.value)

        mesh_ids = {link.mesh_asset_id for link in self.tooth_meshes}

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
                if delta.mesh_asset_id and delta.mesh_asset_id not in mesh_ids:
                    raise ValueError(
                        "tooth delta references unknown segmented mesh asset "
                        f"{delta.mesh_asset_id!r}"
                    )
        return self
