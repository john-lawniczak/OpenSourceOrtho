from __future__ import annotations

import math
from dataclasses import dataclass

from orthoplan.arch_contract import arch_from_tooth_value
from orthoplan.mesh_intersect import triangles_intersect
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
    triangle_distance_mm: float | None
    ipr_mm: float
    sample_based: bool
    triangle_based: bool


def staged_contact_candidates(
    plan: TreatmentPlan,
    bounds_by_tooth: dict[str, BoundingBox],
    *,
    triangles_by_tooth: dict[str, list[tuple[Vec3, Vec3, Vec3]]] | None = None,
) -> dict[tuple[str, str], ContactCandidate]:
    samples = {link.tooth.value: link.surface_sample_points for link in plan.tooth_meshes}
    triangles_by_tooth = triangles_by_tooth or {}
    root_frames = trusted_movement_frames(plan)
    worst: dict[tuple[str, str], ContactCandidate] = {}
    for frame in build_stage_progress_frames(plan):
        moved_bounds = dict(bounds_by_tooth)
        moved_samples = dict(samples)
        moved_triangles = dict(triangles_by_tooth)
        for pose in frame.poses:
            tooth = pose.tooth.value
            if tooth in bounds_by_tooth:
                moved_bounds[tooth] = translate_bounds(bounds_by_tooth[tooth], pose)
            if samples.get(tooth):
                root_frame = root_frames.get(tooth)
                moved_samples[tooth] = [
                    apply_pose_to_vertex(point, pose, root_frame) for point in samples[tooth]
                ]
            if triangles_by_tooth.get(tooth):
                root_frame = root_frames.get(tooth)
                moved_triangles[tooth] = [
                    tuple(apply_pose_to_vertex(point, pose, root_frame) for point in tri)  # type: ignore[misc]
                    for tri in triangles_by_tooth[tooth]
                ]
        for tooth_a, tooth_b in adjacent_pairs(sorted(moved_bounds)):
            overlap = overlap_depth(moved_bounds[tooth_a], moved_bounds[tooth_b])
            if overlap <= 0:
                continue
            candidate = _candidate(
                tooth_a, tooth_b, frame.stage_index, overlap, moved_samples, moved_triangles
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
    triangles: dict[str, list[tuple[Vec3, Vec3, Vec3]]],
) -> ContactCandidate:
    tris_a = triangles.get(tooth_a) or []
    tris_b = triangles.get(tooth_b) or []
    if tris_a and tris_b:
        distance = _min_triangle_distance(tris_a, tris_b)
        return ContactCandidate(tooth_a, tooth_b, stage_index, overlap, None, distance, overlap, False, True)
    points_a = samples.get(tooth_a) or []
    points_b = samples.get(tooth_b) or []
    if points_a and points_b:
        distance = _min_distance(points_a, points_b)
        return ContactCandidate(tooth_a, tooth_b, stage_index, overlap, distance, None, overlap, True, False)
    return ContactCandidate(tooth_a, tooth_b, stage_index, overlap, overlap, None, overlap, False, False)


def _min_distance(points_a: list[Vec3], points_b: list[Vec3]) -> float:
    return min(
        math.dist(a, b)
        for a in points_a
        for b in points_b
    )


def _min_triangle_distance(
    triangles_a: list[tuple[Vec3, Vec3, Vec3]],
    triangles_b: list[tuple[Vec3, Vec3, Vec3]],
) -> float:
    best = math.inf
    for tri_a in triangles_a:
        for tri_b in triangles_b:
            if triangles_intersect(tri_a, tri_b):
                return 0.0
            best = min(best, _triangle_distance(tri_a, tri_b))
    return 0.0 if not math.isfinite(best) else best


def _triangle_distance(a: tuple[Vec3, Vec3, Vec3], b: tuple[Vec3, Vec3, Vec3]) -> float:
    candidates = [
        *(_point_triangle_distance(point, b) for point in a),
        *(_point_triangle_distance(point, a) for point in b),
    ]
    for i in range(3):
        for j in range(3):
            candidates.append(_segment_distance(a[i], a[(i + 1) % 3], b[j], b[(j + 1) % 3]))
    return min(candidates)


def _point_triangle_distance(point: Vec3, tri: tuple[Vec3, Vec3, Vec3]) -> float:
    # Real-Time Collision Detection, Christer Ericson, closest point on triangle.
    a, b, c = tri
    ab = _sub(b, a)
    ac = _sub(c, a)
    ap = _sub(point, a)
    d1 = _dot(ab, ap)
    d2 = _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return math.dist(point, a)
    bp = _sub(point, b)
    d3 = _dot(ab, bp)
    d4 = _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return math.dist(point, b)
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return math.dist(point, _add(a, _scale(ab, v)))
    cp = _sub(point, c)
    d5 = _dot(ab, cp)
    d6 = _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return math.dist(point, c)
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return math.dist(point, _add(a, _scale(ac, w)))
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return math.dist(point, _add(b, _scale(_sub(c, b), w)))
    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    closest = _add(a, _add(_scale(ab, v), _scale(ac, w)))
    return math.dist(point, closest)


def _segment_distance(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> float:
    d1 = _sub(q1, p1)
    d2 = _sub(q2, p2)
    r = _sub(p1, p2)
    a = _dot(d1, d1)
    e = _dot(d2, d2)
    f = _dot(d2, r)
    if a <= 1e-12 and e <= 1e-12:
        return math.dist(p1, p2)
    if a <= 1e-12:
        s = 0.0
        t = _clamp(f / e)
    else:
        c = _dot(d1, r)
        if e <= 1e-12:
            t = 0.0
            s = _clamp(-c / a)
        else:
            b = _dot(d1, d2)
            denom = a * e - b * b
            s = _clamp((b * f - c * e) / denom) if denom != 0.0 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = _clamp(-c / a)
            elif t > 1.0:
                t = 1.0
                s = _clamp((b - c) / a)
    c1 = _add(p1, _scale(d1, s))
    c2 = _add(p2, _scale(d2, t))
    return math.dist(c1, c2)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vec3, scalar: float) -> Vec3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


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
