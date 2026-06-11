from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.plan import TreatmentPlan
from orthoplan.planning.biomechanics import (
    ROOT_AWARE_PIVOT_LABEL,
    apply_pose_to_vertex,
    trusted_movement_frames,
)
from orthoplan.planning.transforms import ToothPose
from orthoplan.viz.progress import build_stage_progress_frames

Vec3 = tuple[float, float, float]


class TransformedToothMesh(BaseModel):
    tooth: str
    mesh_asset_id: str
    vertices: list[Vec3] = Field(default_factory=list)
    transform_note: str


class StageMeshFrame(BaseModel):
    stage_index: int
    meshes: list[TransformedToothMesh] = Field(default_factory=list)
    missing_mesh_asset_ids: list[str] = Field(default_factory=list)


def build_transformed_mesh_frames(
    plan: TreatmentPlan,
    vertices_by_asset_id: dict[str, list[Vec3]],
) -> list[StageMeshFrame]:
    """Transform externally supplied segmented tooth vertices by stage pose.

    Plan JSON stores mesh metadata and redacted references, not mesh bytes. This
    function is the geometry bridge for callers that have loaded the real
    per-tooth vertices from a trusted local source.
    """

    links = {link.tooth.value: link for link in plan.tooth_meshes}
    root_frames = trusted_movement_frames(plan)
    frames = []
    for frame in build_stage_progress_frames(plan):
        meshes: list[TransformedToothMesh] = []
        missing: list[str] = []
        for pose in frame.poses:
            link = links.get(pose.tooth.value)
            if not link:
                continue
            vertices = vertices_by_asset_id.get(link.mesh_asset_id)
            if vertices is None:
                missing.append(link.mesh_asset_id)
                continue
            movement_frame = root_frames.get(pose.tooth.value)
            meshes.append(
                TransformedToothMesh(
                    tooth=pose.tooth.value,
                    mesh_asset_id=link.mesh_asset_id,
                    vertices=[
                        apply_pose_to_vertex(vertex, pose, movement_frame) for vertex in vertices
                    ],
                    transform_note=_transform_note(movement_frame is not None),
                )
            )
        frames.append(StageMeshFrame(stage_index=frame.stage_index, meshes=meshes, missing_mesh_asset_ids=missing))
    return frames


def _transform_note(root_aware: bool) -> str:
    if root_aware:
        return (
            "Applied cumulative translation and trusted root-aware rotation about "
            f"{ROOT_AWARE_PIVOT_LABEL}."
        )
    return (
        "Applied cumulative translation in millimeters. Rotation remains a "
        "crown-centroid visualization assumption because trusted root anatomy is unavailable."
    )
