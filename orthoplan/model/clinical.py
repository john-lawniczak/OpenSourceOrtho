from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from orthoplan.model.identity import ToothId

MovementAxis = Literal[
    "translate_x",
    "translate_y",
    "translate_z",
    "tip",
    "torque",
    "rotation",
    "all",
]


class FixedTooth(BaseModel):
    """A tooth intended to remain stationary for part or all of the plan."""

    tooth: ToothId
    stage_start: int = Field(default=0, ge=0)
    stage_end: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @model_validator(mode="after")
    def end_not_before_start(self) -> FixedTooth:
        if self.stage_end is not None and self.stage_end < self.stage_start:
            raise ValueError("fixed tooth stage_end must be greater than or equal to stage_start")
        return self

    def applies_to(self, stage_index: int) -> bool:
        return stage_index >= self.stage_start and (
            self.stage_end is None or stage_index <= self.stage_end
        )


class MovementExclusion(BaseModel):
    """A clinician-authored movement axis exclusion for a tooth."""

    tooth: ToothId
    axes: set[MovementAxis] = Field(default_factory=set)
    stage_start: int = Field(default=0, ge=0)
    stage_end: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @field_validator("axes")
    @classmethod
    def axes_are_present(cls, axes: set[MovementAxis]) -> set[MovementAxis]:
        if not axes:
            raise ValueError("movement exclusion must list at least one axis")
        return axes

    @model_validator(mode="after")
    def end_not_before_start(self) -> MovementExclusion:
        if self.stage_end is not None and self.stage_end < self.stage_start:
            raise ValueError("movement exclusion stage_end must be greater than or equal to stage_start")
        return self

    def applies_to(self, stage_index: int, axis: MovementAxis) -> bool:
        return stage_index >= self.stage_start and (
            self.stage_end is None or stage_index <= self.stage_end
        ) and ("all" in self.axes or axis in self.axes)


AttachmentType = Literal[
    "optimized",
    "vertical_rectangular",
    "horizontal_rectangular",
    "beveled",
    "ellipsoid",
    "button",
]


class Attachment(BaseModel):
    """Planned aligner auxiliary metadata.

    This records clinical intent only. It is not a force model and does not
    imply that a movement will express as planned.
    """

    tooth: ToothId
    type: AttachmentType = "vertical_rectangular"
    surface: Literal["buccal", "lingual", "occlusal"] = "buccal"
    stage_start: int = Field(default=0, ge=0)
    stage_end: int | None = Field(default=None, ge=0)
    purpose: str | None = None

    @model_validator(mode="after")
    def end_not_before_start(self) -> Attachment:
        if self.stage_end is not None and self.stage_end < self.stage_start:
            raise ValueError("attachment stage_end must be greater than or equal to stage_start")
        return self

    def applies_to(self, stage_index: int) -> bool:
        return stage_index >= self.stage_start and (
            self.stage_end is None or stage_index <= self.stage_end
        )


class InterproximalReduction(BaseModel):
    """IPR planned between adjacent teeth, in millimeters."""

    tooth_a: ToothId
    tooth_b: ToothId
    amount_mm: float = Field(gt=0)
    stage_index: int = Field(default=0, ge=0)
    source: Literal["manual", "imported", "model"] = "manual"
    notes: str | None = None

    @model_validator(mode="after")
    def teeth_are_distinct(self) -> InterproximalReduction:
        if self.tooth_a.value == self.tooth_b.value:
            raise ValueError("IPR teeth must be distinct")
        return self

    @property
    def contact_key(self) -> tuple[str, str]:
        return tuple(sorted((self.tooth_a.value, self.tooth_b.value)))  # type: ignore[return-value]


class PlannedSpacing(BaseModel):
    """A planned residual/open contact space between two teeth."""

    tooth_a: ToothId
    tooth_b: ToothId
    amount_mm: float = Field(gt=0)
    stage_index: int = Field(default=0, ge=0)
    reason: str | None = None

    @model_validator(mode="after")
    def teeth_are_distinct(self) -> PlannedSpacing:
        if self.tooth_a.value == self.tooth_b.value:
            raise ValueError("spacing teeth must be distinct")
        return self

    @property
    def contact_key(self) -> tuple[str, str]:
        return tuple(sorted((self.tooth_a.value, self.tooth_b.value)))  # type: ignore[return-value]
