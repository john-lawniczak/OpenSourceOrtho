from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

CAPS_REFERENCE = (
    "Heuristic defaults from clear-aligner staging literature; clinician must configure."
)


class AxisCaps(BaseModel):
    """Per-stage movement caps for a single tooth class.

    Semantics (see geometry.py for axis definitions):

    - ``linear_mm`` caps the Euclidean magnitude of horizontal movement
      (x/y combined), not each axis independently.
    - ``intrusion_extrusion_mm`` caps vertical (z / occlusogingival) movement.
    - ``angular_deg`` caps tip and torque.
    - ``rotation_deg`` caps long-axis rotation.

    Defaults are conservative planning heuristics, not clinical clearance.
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
    planning.timeline) so a clinical-looking estimate is never persisted.
    """

    wear_interval_days: int = Field(default=14, gt=0)


class TreatmentSettings(BaseModel):
    movement_caps: MovementCaps = Field(default_factory=MovementCaps)
    timeline: TimelineSettings = Field(default_factory=TimelineSettings)
