from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.transforms import ToothPose

# Re-exported so existing importers of ToothPose from viz keep working.
__all__ = ["ProgressViewMode", "ToothPose", "StageProgressFrame", "build_stage_progress_frames"]


class ProgressViewMode(StrEnum):
    CURRENT = "current"
    PLANNED = "planned"
    OVERLAY = "overlay"
    STAGE = "stage"


class StageProgressFrame(BaseModel):
    stage_index: int = Field(ge=0)
    poses: list[ToothPose] = Field(default_factory=list)
    coordinate_frame: str = "scan-local"
    rotation_renderable: bool = False
    data_gaps: list[str] = Field(default_factory=list)


def build_stage_progress_frames(plan: TreatmentPlan) -> list[StageProgressFrame]:
    """Build cumulative frames so UIs render progress from one canonical contract.

    The viz layer does not recompute movement policy: it consumes pose
    composition from ``planning.transforms`` and gaps from ``model.gaps``.
    """

    rotation_renderable = plan.coordinate_frame.tip_torque_convertible
    frame_name = plan.coordinate_frame.name
    gaps = data_gaps(plan)

    poses: dict[str, ToothPose] = {}
    frames: list[StageProgressFrame] = []

    for stage in plan.stages:
        for delta in stage.deltas:
            key = delta.tooth.value
            if key in poses:
                poses[key] = poses[key].apply_delta(delta)
            else:
                poses[key] = ToothPose.from_delta(delta, rotation_renderable=rotation_renderable)

        frames.append(
            StageProgressFrame(
                stage_index=stage.index,
                poses=sorted(poses.values(), key=lambda pose: pose.tooth.value),
                coordinate_frame=frame_name,
                rotation_renderable=rotation_renderable,
                data_gaps=gaps,
            )
        )

    return frames
