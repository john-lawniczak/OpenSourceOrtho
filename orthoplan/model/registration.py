"""STL-to-CBCT registration transform and quality.

A ``RegistrationTransform`` records how a surface scan (STL mesh asset) aligns to
a CBCT/DICOM record: the 4x4 transform, the method, operator/model provenance, a
quality score, and an explicit ``accepted`` flag. Acceptance is fail-closed - a
registration only gates CBCT-derived checks when it is BOTH accepted AND carries
quality metrics (see ``accepted_registration``).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

Matrix4 = list[list[float]]


class RegistrationMethod(StrEnum):
    MANUAL = "manual"
    IMPORTED = "imported"
    AUTOMATIC_ICP = "automatic-icp"


class RegistrationQuality(BaseModel):
    """Geometric registration quality metrics. Review aids, not a diagnosis."""

    method: str
    rmse_mm: float | None = Field(default=None, ge=0)
    inlier_ratio: float | None = Field(default=None, ge=0, le=1)
    fitness: float | None = Field(default=None, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


def _identity4() -> Matrix4:
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


class RegistrationTransform(BaseModel):
    id: str
    source_stl_asset_id: str
    target_cbct_record_id: str
    method: RegistrationMethod = RegistrationMethod.MANUAL
    matrix: Matrix4 = Field(default_factory=_identity4)
    operator: str | None = None
    model_provenance: str | None = None
    quality: RegistrationQuality | None = None
    accepted: bool = False
    notes: str | None = None

    @field_validator("matrix")
    @classmethod
    def matrix_is_4x4_affine(cls, value: Matrix4) -> Matrix4:
        if len(value) != 4 or any(len(row) != 4 for row in value):
            raise ValueError("registration matrix must be 4x4")
        last = value[3]
        if [round(v, 9) for v in last] != [0.0, 0.0, 0.0, 1.0]:
            raise ValueError("registration matrix bottom row must be [0, 0, 0, 1]")
        return value

    @property
    def is_acceptable(self) -> bool:
        """Accepted AND backed by quality metrics (fail-closed gate input)."""

        return self.accepted and self.quality is not None
