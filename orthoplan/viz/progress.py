from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from orthoplan.model import ToothDelta, ToothId, TreatmentPlan


class ProgressViewMode(StrEnum):
    CURRENT = "current"
    PLANNED = "planned"
    OVERLAY = "overlay"
    STAGE = "stage"


class ToothPose(BaseModel):
    """Cumulative tooth pose for visualization in explicit movement units."""

    model_config = ConfigDict(frozen=True)

    tooth: ToothId
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0
    translate_z_mm: float = 0.0
    rotate_tip_deg: float = 0.0
    rotate_torque_deg: float = 0.0
    rotate_rotation_deg: float = 0.0
    coordinate_frame: str = "scan-local-right-handed"
    source: str = "plan"

    @classmethod
    def from_delta(cls, delta: ToothDelta) -> "ToothPose":
        return cls(
            tooth=delta.tooth,
            translate_x_mm=delta.translate_x_mm,
            translate_y_mm=delta.translate_y_mm,
            translate_z_mm=delta.translate_z_mm,
            rotate_tip_deg=delta.rotate_tip_deg,
            rotate_torque_deg=delta.rotate_torque_deg,
            rotate_rotation_deg=delta.rotate_rotation_deg,
            coordinate_frame=delta.coordinate_frame,
            source=delta.source,
        )

    def apply_delta(self, delta: ToothDelta) -> "ToothPose":
        if (delta.tooth.system, delta.tooth.value) != (self.tooth.system, self.tooth.value):
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


class StageProgressFrame(BaseModel):
    stage_index: int = Field(ge=0)
    poses: list[ToothPose] = Field(default_factory=list)
    coordinate_frame: str = "scan-local-right-handed"
    data_gaps: list[str] = Field(default_factory=list)


def build_stage_progress_frames(plan: TreatmentPlan) -> list[StageProgressFrame]:
    """Build cumulative frames so UIs render progress from one canonical contract."""

    poses: dict[tuple[str, str], ToothPose] = {}
    frames: list[StageProgressFrame] = []
    data_gaps = _data_gaps(plan)

    for stage in plan.stages:
        for delta in stage.deltas:
            key = (delta.tooth.system, delta.tooth.value)
            if key in poses:
                poses[key] = poses[key].apply_delta(delta)
            else:
                poses[key] = ToothPose.from_delta(delta)

        coordinate_frames = {pose.coordinate_frame for pose in poses.values()}
        frame_coordinate = coordinate_frames.pop() if len(coordinate_frames) == 1 else "mixed"
        frames.append(
            StageProgressFrame(
                stage_index=stage.index,
                poses=sorted(poses.values(), key=lambda pose: (pose.tooth.system, pose.tooth.value)),
                coordinate_frame=frame_coordinate,
                data_gaps=data_gaps,
            )
        )

    return frames


def _data_gaps(plan: TreatmentPlan) -> list[str]:
    gaps: list[str] = []
    data = plan.data
    if not data.roots:
        gaps.append("roots unavailable")
    if not data.cbct:
        gaps.append("CBCT unavailable")
    if not data.periodontal_status:
        gaps.append("periodontal status unavailable")
    if not data.occlusion_scan:
        gaps.append("occlusion scan unavailable")
    if not data.clinician_notes:
        gaps.append("clinician notes unavailable")
    return gaps

