"""Cumulative tooth-pose composition.

Ownership: transforms live in ``planning`` so that ``viz`` consumes a finished
contract rather than recomputing movement (see MAINTAINABILITY.md).

Phase 1 honesty rules:

- Translation is a true vector sum (translation is commutative and additive),
  so cumulative translation is geometrically correct.
- Rotation is reported as the sum of authored components about each named axis.
  Euler-angle sums are NOT a composable rigid rotation, so they are flagged
  ``rotation_renderable=False`` whenever the coordinate frame cannot convert
  tip/torque/long-axis rotation (the Phase 1 scan frame cannot). A UI MUST NOT
  build a rotation matrix from a non-renderable pose.
- The visualization pivot is the crown centroid. This is a visualization
  assumption, not a biomechanical claim, and never implies root position.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from orthoplan.model.plan import ToothDelta, ToothId

PIVOT_LABEL = "crown-centroid (visualization assumption, not biomechanics)"


class ToothPose(BaseModel):
    """Cumulative tooth pose for visualization in explicit units."""

    model_config = ConfigDict(frozen=True)

    tooth: ToothId
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0
    translate_z_mm: float = 0.0
    rotate_tip_deg: float = 0.0
    rotate_torque_deg: float = 0.0
    rotate_rotation_deg: float = 0.0
    coordinate_frame: str = "scan-local"
    rotation_renderable: bool = False
    pivot: str = PIVOT_LABEL
    source: str = "plan"

    def ui_dict(self) -> dict:
        """UI-shaped serialization: every model field, with tooth flattened to
        its FDI value. Derived from ``model_dump`` so new fields can never
        silently drop out of the client contract."""
        data = self.model_dump()
        data["tooth"] = self.tooth.value
        return data

    @classmethod
    def from_delta(cls, delta: ToothDelta, *, rotation_renderable: bool) -> "ToothPose":
        return cls(
            tooth=delta.tooth,
            translate_x_mm=delta.translate_x_mm,
            translate_y_mm=delta.translate_y_mm,
            translate_z_mm=delta.translate_z_mm,
            rotate_tip_deg=delta.rotate_tip_deg,
            rotate_torque_deg=delta.rotate_torque_deg,
            rotate_rotation_deg=delta.rotate_rotation_deg,
            coordinate_frame=delta.coordinate_frame,
            rotation_renderable=rotation_renderable,
            source=delta.source,
        )

    def apply_delta(self, delta: ToothDelta) -> "ToothPose":
        if delta.tooth.value != self.tooth.value:
            raise ValueError("cannot apply a delta for a different tooth")
        if delta.coordinate_frame != self.coordinate_frame:
            raise ValueError("cannot combine deltas from different coordinate frames")

        return self.model_copy(
            update={
                "translate_x_mm": self.translate_x_mm + delta.translate_x_mm,
                "translate_y_mm": self.translate_y_mm + delta.translate_y_mm,
                "translate_z_mm": self.translate_z_mm + delta.translate_z_mm,
                "rotate_tip_deg": self.rotate_tip_deg + delta.rotate_tip_deg,
                "rotate_torque_deg": self.rotate_torque_deg + delta.rotate_torque_deg,
                "rotate_rotation_deg": self.rotate_rotation_deg + delta.rotate_rotation_deg,
                "source": delta.source,
            }
        )
