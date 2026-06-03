from __future__ import annotations

from pydantic import BaseModel, Field


class MovementCaps(BaseModel):
    """Clinician-configurable per-stage movement caps.

    Defaults are conservative clear-aligner planning heuristics, not clinical clearance.
    """

    linear_mm: float = Field(default=0.25, gt=0)
    angular_deg: float = Field(default=1.0, gt=0)
    rotation_deg: float = Field(default=2.0, gt=0)
    intrusion_extrusion_mm: float = Field(default=0.10, gt=0)
    reference: str = (
        "Heuristic defaults from clear-aligner staging literature; clinician must configure."
    )


class TreatmentSettings(BaseModel):
    movement_caps: MovementCaps = Field(default_factory=MovementCaps)

