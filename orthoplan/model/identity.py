from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
