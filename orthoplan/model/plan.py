from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from orthoplan.model.settings import TreatmentSettings


class Arch(StrEnum):
    MAXILLARY = "maxillary"
    MANDIBULAR = "mandibular"


NumberingSystem = Literal["FDI", "Universal", "Palmer"]


class ToothId(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: NumberingSystem = "FDI"
    value: str = Field(min_length=1)


class ToothDelta(BaseModel):
    """A proposed tooth movement in explicit units."""

    tooth: ToothId
    arch: Arch
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0
    translate_z_mm: float = 0.0
    rotate_tip_deg: float = 0.0
    rotate_torque_deg: float = 0.0
    rotate_rotation_deg: float = 0.0
    coordinate_frame: str = "scan-local-right-handed"
    source: Literal["manual", "imported", "model", "synthetic"] = "manual"


class Stage(BaseModel):
    index: int = Field(ge=0)
    deltas: list[ToothDelta] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("deltas")
    @classmethod
    def unique_teeth(cls, deltas: list[ToothDelta]) -> list[ToothDelta]:
        seen: set[tuple[str, str]] = set()
        for delta in deltas:
            key = (delta.tooth.system, delta.tooth.value)
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


class TreatmentPlan(BaseModel):
    id: str
    title: str = "Untitled plan"
    numbering_system: NumberingSystem = "FDI"
    data: DataAvailability = Field(default_factory=DataAvailability)
    settings: TreatmentSettings = Field(default_factory=TreatmentSettings)
    stages: list[Stage] = Field(default_factory=list)

    @field_validator("stages")
    @classmethod
    def stage_indexes_are_contiguous(cls, stages: list[Stage]) -> list[Stage]:
        indexes = [stage.index for stage in stages]
        if indexes != list(range(len(stages))):
            raise ValueError("stage indexes must be contiguous and start at 0")
        return stages
