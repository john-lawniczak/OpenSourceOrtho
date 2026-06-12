"""Reviewed CBCT-derived anatomy: roots, tooth axes, and alveolar bone.

Every derived-anatomy object is provenance-bound (source CBCT record, the
registration that placed it, the model/operator that produced it, a confidence,
and a human review status) and FAIL-CLOSED: it is only ``trusted`` for downstream
root/bone-aware checks when a human has accepted or corrected it AND it is in
field. Proposed, rejected, uncertain, or out-of-field anatomy is never trusted.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Union

from pydantic import BaseModel, Field

from orthoplan.model.geometry import Vec3
from orthoplan.model.identity import ToothId


class ReviewStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class DerivedAnatomyProvenance(BaseModel):
    """Shared provenance + review fields for every derived-anatomy object."""

    source_cbct_record_id: str
    registration_id: str
    model_provenance: str | None = None
    operator: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    out_of_field: bool = False
    notes: list[str] = Field(default_factory=list)
    quality_metrics: dict[str, Union[bool, float, int, str]] = Field(default_factory=dict)

    @property
    def reviewed(self) -> bool:
        return self.review_status in (ReviewStatus.ACCEPTED, ReviewStatus.CORRECTED)

    @property
    def trusted(self) -> bool:
        """Reviewed AND in field. The single gate downstream checks must use."""

        return self.reviewed and not self.out_of_field


class RootGeometry(DerivedAnatomyProvenance):
    """A per-tooth root mesh asset and/or a root centerline polyline."""

    tooth: ToothId
    mesh_asset_id: str | None = None
    centerline: list[Vec3] = Field(default_factory=list)


class ToothAxis(DerivedAnatomyProvenance):
    """A trusted long-axis for a tooth derived from reviewed crown/root anatomy."""

    tooth: ToothId
    origin_mm: Vec3
    direction: Vec3
    derived_from: str = "crown+root"


class AlveolarBoneRecord(DerivedAnatomyProvenance):
    """An alveolar bone surface mesh and/or a boundary-volume reference."""

    region: str = "full-arch"
    mesh_asset_id: str | None = None
    boundary_volume_reference: str | None = None


class DerivedAnatomy(BaseModel):
    """Container for all reviewed CBCT-derived anatomy on a plan."""

    roots: list[RootGeometry] = Field(default_factory=list)
    tooth_axes: list[ToothAxis] = Field(default_factory=list)
    alveolar_bone: list[AlveolarBoneRecord] = Field(default_factory=list)

    def all_objects(self) -> list[DerivedAnatomyProvenance]:
        return [*self.roots, *self.tooth_axes, *self.alveolar_bone]

    @property
    def has_trusted(self) -> bool:
        return any(obj.trusted for obj in self.all_objects())

    def trusted_root_teeth(self) -> set[str]:
        return {r.tooth.value for r in self.roots if r.trusted}

    def trusted_axis_teeth(self) -> set[str]:
        return {a.tooth.value for a in self.tooth_axes if a.trusted}
