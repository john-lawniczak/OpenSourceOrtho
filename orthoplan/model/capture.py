"""Declared acquisition provenance; neither geometry validation nor treatment data."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

CaptureKind = Literal["intraoral_scan", "cast_scan", "impression_scan", "aligner_scan",
                      "printed_model_scan", "unknown"]


class CaptureProvenance(BaseModel):
    """Optional metadata on the exact hashed scan in a contribution manifest.

    Unknowns remain explicit. Parent hashes identify digital inputs, not a claim
    that physical impressions, casts or tooth positions have been verified.
    """

    model_config = {"extra": "forbid"}

    kind: CaptureKind = "unknown"
    acquired_on: date | None = None
    physical_object_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    capture_session_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    surface: Literal["dentition", "negative_impression", "appliance_inner",
                     "appliance_outer", "appliance_both", "unknown"] = "unknown"
    condition: Literal["intact", "chipped", "fractured", "reassembled", "unknown"] = "unknown"
    fragment_count: int | None = Field(default=None, ge=1)
    support_material: str | None = Field(default=None, max_length=120)
    scanner: str | None = Field(default=None, max_length=120)
    material: str | None = Field(default=None, max_length=120)
    coating: Literal["none", "applied", "unknown"] = "unknown"
    coating_product: str | None = Field(default=None, max_length=120)
    processing: list[Literal["trimmed", "smoothed", "hole_filled", "remeshed", "scaled",
                            "registered", "unknown"]] = Field(default_factory=lambda: ["unknown"])
    parent_sha256: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def consistent_surface_and_parents(self):
        import re
        permitted = {
            "intraoral_scan": {"dentition", "unknown"},
            "cast_scan": {"dentition", "unknown"},
            "printed_model_scan": {"dentition", "unknown"},
            "impression_scan": {"negative_impression", "unknown"},
            "aligner_scan": {"appliance_inner", "appliance_outer", "appliance_both", "unknown"},
        }
        if self.kind in permitted and self.surface not in permitted[self.kind]:
            raise ValueError("Surface identity conflicts with capture kind")
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in self.parent_sha256):
            raise ValueError("Digital parent hashes must be lowercase SHA-256 values")
        if self.condition == "intact" and self.fragment_count not in {None, 1}:
            raise ValueError("An intact specimen cannot have multiple fragments")
        if self.condition in {"fractured", "reassembled"} and self.fragment_count == 1:
            raise ValueError("A fractured or reassembled specimen cannot declare one fragment")
        if self.coating == "none" and self.coating_product:
            raise ValueError("A coating product conflicts with coating=none")
        return self
