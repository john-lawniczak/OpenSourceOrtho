from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

CAPS_REFERENCE = (
    "Heuristic defaults from clear-aligner staging literature; user-configurable."
)


class AxisCaps(BaseModel):
    """Per-stage movement caps for a single tooth class.

    Semantics (see geometry.py for axis definitions):

    - ``linear_mm`` caps the Euclidean magnitude of horizontal movement
      (x/y combined), not each axis independently.
    - ``intrusion_extrusion_mm`` caps vertical (z / occlusogingival) movement.
    - ``angular_deg`` caps tip and torque.
    - ``rotation_deg`` caps long-axis rotation.

    Defaults are planning heuristics, not clearance.
    """

    linear_mm: float = Field(default=0.25, gt=0)
    angular_deg: float = Field(default=1.0, gt=0)
    rotation_deg: float = Field(default=2.0, gt=0)
    intrusion_extrusion_mm: float = Field(default=0.10, gt=0)
    reference: str = CAPS_REFERENCE


class MovementCaps(BaseModel):
    """Clinician-configurable movement caps.

    ``default`` applies to every tooth. ``per_tooth_overrides`` is reserved for
    later phases so tooth-class-specific caps can be added without changing the
    rule interface; the key is a canonical FDI tooth id.
    """

    default: AxisCaps = Field(default_factory=AxisCaps)
    per_tooth_overrides: dict[str, AxisCaps] = Field(default_factory=dict)

    @field_validator("per_tooth_overrides")
    @classmethod
    def override_keys_are_fdi(cls, value: dict[str, AxisCaps]) -> dict[str, AxisCaps]:
        for key in value:
            if (
                len(key) != 2
                or not key.isdigit()
                or key[0] not in {"1", "2", "3", "4", "5", "6", "7", "8"}
                or key[1] not in {"1", "2", "3", "4", "5", "6", "7", "8"}
            ):
                raise ValueError(f"movement cap override key must be canonical FDI, got {key!r}")
        return value

    def caps_for(self, tooth_value: str) -> AxisCaps:
        return self.per_tooth_overrides.get(tooth_value, self.default)


class TimelineSettings(BaseModel):
    """Inputs for the arithmetic timeline projection.

    Only inputs are stored. Duration is computed dynamically (see
    planning.timeline) so an outcome-looking estimate is never persisted.
    """

    wear_interval_days: int = Field(default=14, gt=0)


class PrintExportSettings(BaseModel):
    """Requested 3D-print/thermoforming handoff settings.

    This stores export intent and process metadata only. It does not make a plan
    approved, safe, or manufacture-ready.
    """

    enabled: bool = False
    export_format: Literal["stl", "3mf"] = "stl"
    delivery_email: str | None = None
    model_material: str = "validated dental model resin"
    thermoforming_material: str = "user-selected aligner sheet material"
    safety_acknowledged: bool = False
    post_processing_notes: str = (
        "Cure and clean printed models per material instructions; remove supports and "
        "smooth model artifacts before thermoforming. Do not alter aligner plastic unless "
        "the material instructions and chosen process explicitly allow it."
    )

    @field_validator("delivery_email")
    @classmethod
    def delivery_email_is_basic_address(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("delivery_email must look like an email address")
        return value


class TreatmentSettings(BaseModel):
    movement_caps: MovementCaps = Field(default_factory=MovementCaps)
    timeline: TimelineSettings = Field(default_factory=TimelineSettings)
    print_export: PrintExportSettings = Field(default_factory=PrintExportSettings)
