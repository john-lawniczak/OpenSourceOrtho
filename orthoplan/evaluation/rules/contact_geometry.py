from __future__ import annotations

import math
from dataclasses import dataclass

from orthoplan.arch_contract import arch_from_tooth_value
from orthoplan.model.assets import BoundingBox
from orthoplan.model.geometry import Vec3
from orthoplan.model.plan import SegmentedToothMesh, TreatmentPlan
from orthoplan.planning.biomechanics import apply_pose_to_vertex, trusted_movement_frames
from orthoplan.viz.progress import build_stage_progress_frames


@dataclass(frozen=True)
class ContactCandidate:
    tooth_a: str
    tooth_b: str
    stage_index: int
    bbox_overlap_mm: float
    sample_distance_mm: float | None
    ipr_mm: float
    sample_based: bool


def staged_contact_candidates(
    plan: TreatmentPlan, bounds_by_tooth: dict[str, BoundingBox]
) -> dict[tuple[str, str], ContactCandidate]:
    samples = {link.tooth.value: link.surface_sample_points for link in plan.tooth_meshes}
    root_frames = trusted_movement_frames(plan)
    worst: dict[tuple[str, str], ContactCandidate] = {}
    for frame in build_stage_progress_frames(plan):
        moved_bounds = dict(bounds_by_tooth)
        moved_samples = dict(samples)
        for pose in frame.poses:
            tooth = pose.tooth.value
            if tooth in bounds_by_tooth:
                moved_bounds[tooth] = translate_bounds(bounds_by_tooth[tooth], pose)
            if samples.get(tooth):
                root_frame = root_frames.get(tooth)
                moved_samples[tooth] = [
                    apply_pose_to_vertex(point, pose, root_frame) for point in samples[tooth]
                ]
        for tooth_a, tooth_b in adjacent_pairs(sorted(moved_bounds)):
            overlap = overlap_depth(moved_bounds[tooth_a], moved_bounds[tooth_b])
            if overlap <= 0:
                continue
            candidate = _candidate(
                tooth_a, tooth_b, frame.stage_index, overlap, moved_samples
            )
            key = (tooth_a, tooth_b)
            if key not in worst or candidate.ipr_mm > worst[key].ipr_mm:
                worst[key] = candidate
    return worst


def translate_bounds(bounds: BoundingBox, pose) -> BoundingBox:
    delta = (pose.translate_x_mm, pose.translate_y_mm, pose.translate_z_mm)
    return BoundingBox(
        min_xyz=tuple(bounds.min_xyz[i] + delta[i] for i in range(3)),  # type: ignore[return-value]
        max_xyz=tuple(bounds.max_xyz[i] + delta[i] for i in range(3)),  # type: ignore[return-value]
    )


def overlap_depth(a: BoundingBox, b: BoundingBox) -> float:
    depths = []
    for axis in range(3):
        depth = min(a.max_xyz[axis], b.max_xyz[axis]) - max(a.min_xyz[axis], b.min_xyz[axis])
        if depth <= 0:
            return 0.0
        depths.append(depth)
    return min(depths)


def adjacent_pairs(teeth: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    by_arch: dict[str, list[str]] = {}
    for tooth in teeth:
        by_arch.setdefault(arch_from_tooth_value(tooth), []).append(tooth)
    for arch, values in by_arch.items():
        ordered = _arch_order(arch, values)
        pairs.extend((ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1))
    return pairs


def _candidate(
    tooth_a: str,
    tooth_b: str,
    stage_index: int,
    overlap: float,
    samples: dict[str, list[Vec3]],
) -> ContactCandidate:
    points_a = samples.get(tooth_a) or []
    points_b = samples.get(tooth_b) or []
    if points_a and points_b:
        distance = _min_distance(points_a, points_b)
        return ContactCandidate(tooth_a, tooth_b, stage_index, overlap, distance, overlap, True)
    return ContactCandidate(tooth_a, tooth_b, stage_index, overlap, overlap, overlap, False)


def _min_distance(points_a: list[Vec3], points_b: list[Vec3]) -> float:
    return min(
        math.dist(a, b)
        for a in points_a
        for b in points_b
    )


def _arch_order(arch: str, teeth: list[str]) -> list[str]:
    values = sorted(teeth)
    if arch == "maxillary":
        return sorted(values, key=_maxillary_key)
    return sorted(values, key=_mandibular_key)


def _maxillary_key(tooth: str) -> tuple[int, int]:
    quadrant = int(tooth[0])
    number = int(tooth[1])
    return (0, -number) if quadrant == 1 else (1, number)


def _mandibular_key(tooth: str) -> tuple[int, int]:
    quadrant = int(tooth[0])
    number = int(tooth[1])
    return (0, -number) if quadrant == 4 else (1, number)
