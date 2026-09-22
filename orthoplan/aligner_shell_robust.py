"""Optional robust aligner-shell backend (Open3D repair + distance offset).

Gated behind the optional ``mesh-processing`` extra (Open3D), mirroring the
automatic-registration experiment. The pure-Python backend in ``aligner_shell``
assumes consistent outward winding and offsets along raw vertex normals; this
path first repairs the input mesh with Open3D (merge near-duplicate vertices,
drop degenerate triangles, remove non-manifold edges, orient consistently,
recompute robust normals), then uses Open3D's distance queries to correct the
outer surface toward the requested offset distance before the shared shell QA
closes and evaluates the artifact.

This is a signed-distance-style backend, not a clinical manufacturing guarantee.
When Open3D is not installed it fails closed (raises ``RobustShellUnavailable``);
the caller falls back to the pure-Python shell and records the downgrade rather
than silently changing geometry.
"""

from __future__ import annotations

from orthoplan.aligner_shell import ShellResult, TrimPlane, assemble_shell_surfaces
from orthoplan.aligner_shell_topology import boundary_edges, norm

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]
_DISTANCE_TOLERANCE_MM = 1e-4


class RobustShellUnavailable(RuntimeError):
    """Raised when the robust shell backend is requested but Open3D is missing."""


def robust_shell_available() -> bool:
    try:
        import open3d  # noqa: F401
    except ImportError:
        return False
    return True


def build_robust_shell(
    triangles: list[Triangle],
    *,
    thickness_mm: float,
    minimum_printable_feature_mm: float = 0.3,
    trim: TrimPlane | None = None,
    xy_compensation_mm: float = 0.0,
    z_compensation_mm: float = 0.0,
) -> ShellResult:
    """Repair the input mesh with Open3D, then build the shell via the shared path."""

    if thickness_mm <= 0:
        raise ValueError("aligner sheet thickness must be positive")
    verts, faces, normals, dropped, skinny = _repair_mesh(triangles)
    if not faces:
        raise ValueError("aligner shell requires a non-empty surface mesh")
    if trim is not None:
        faces = [f for f in faces if all(trim.keeps(verts[i]) for i in f)]
        if not faces:
            raise ValueError("trim removed the entire surface; check the trim plane")
    inner = _compensated_inner_surface(verts, normals, xy_compensation_mm, z_compensation_mm)
    outer = _distance_offset_surface(inner, normals, faces, thickness_mm)
    return assemble_shell_surfaces(
        inner, outer, faces,
        input_boundary_edges=boundary_edges(faces),
        thickness_mm=thickness_mm,
        minimum_printable_feature_mm=minimum_printable_feature_mm,
        trim_applied=trim is not None,
        xy_compensation_mm=xy_compensation_mm,
        z_compensation_mm=z_compensation_mm,
        dropped=dropped,
        skinny=skinny,
    )


def _repair_mesh(
    triangles: list[Triangle],
) -> tuple[
    list[Vec3], list[tuple[int, int, int]], list[Vec3], int, int
]:  # pragma: no cover - optional extra
    """Open3D mesh repair -> (vertices, faces, normals, dropped_count, skinny_count).

    Guarded so the heavy import only happens when the robust path actually runs.
    """

    np, o3d = _open3d_modules()
    flat = np.asarray(triangles, dtype=float).reshape(-1, 3)
    faces_in = np.arange(len(flat), dtype=np.int64).reshape(-1, 3)
    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(flat),
        o3d.utility.Vector3iVector(faces_in),
    )
    before = len(mesh.triangles)
    mesh.merge_close_vertices(1e-6)
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    mesh.orient_triangles()
    mesh.compute_vertex_normals()
    dropped = max(0, before - len(mesh.triangles))
    verts = [tuple(map(float, v)) for v in np.asarray(mesh.vertices)]
    faces = [tuple(map(int, f)) for f in np.asarray(mesh.triangles)]
    normals = [tuple(map(float, n)) for n in np.asarray(mesh.vertex_normals)]
    return verts, faces, normals, dropped, 0


def _distance_offset_surface(
    inner: list[Vec3],
    normals: list[Vec3],
    faces: list[tuple[int, int, int]],
    thickness_mm: float,
) -> list[Vec3]:  # pragma: no cover - optional extra
    """Offset vertices with an Open3D distance-query correction loop.

    The initial candidate follows repaired vertex normals. A short bracketed
    search then chooses the point along that ray whose nearest-surface distance
    is closest to the requested wall thickness. This gives the robust backend an
    actual distance field check instead of blindly trusting averaged normals.
    """

    np, o3d = _open3d_modules()
    mesh = o3d.t.geometry.TriangleMesh()
    mesh.vertex["positions"] = o3d.core.Tensor(np.asarray(inner), dtype=o3d.core.Dtype.Float32)
    mesh.triangle["indices"] = o3d.core.Tensor(np.asarray(faces), dtype=o3d.core.Dtype.Int32)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh)

    outer: list[Vec3] = []
    for point, normal in zip(inner, normals, strict=True):
        unit = _unit(normal)
        if unit is None:
            outer.append(point)
            continue
        outer.append(_offset_point_by_distance(point, unit, thickness_mm, scene, o3d, np))
    return outer


def _offset_point_by_distance(
    point: Vec3,
    direction: Vec3,
    target: float,
    scene,
    o3d,
    np,
) -> Vec3:  # pragma: no cover - optional extra
    lo = 0.0
    hi = max(target * 2.0, target + 0.25)
    best = _advance(point, direction, target)
    best_error = abs(_scene_distance(best, scene, o3d, np) - target)
    for _ in range(18):
        mid = (lo + hi) / 2.0
        candidate = _advance(point, direction, mid)
        distance = _scene_distance(candidate, scene, o3d, np)
        error = abs(distance - target)
        if error < best_error:
            best = candidate
            best_error = error
        if distance < target:
            lo = mid
        else:
            hi = mid
        if best_error <= _DISTANCE_TOLERANCE_MM:
            break
    return best


def _scene_distance(point: Vec3, scene, o3d, np) -> float:  # pragma: no cover - optional extra
    query = o3d.core.Tensor(np.asarray([point]), dtype=o3d.core.Dtype.Float32)
    return float(scene.compute_distance(query).numpy()[0])


def _compensated_inner_surface(
    verts: list[Vec3],
    normals: list[Vec3],
    xy_compensation_mm: float,
    z_compensation_mm: float,
) -> list[Vec3]:
    return [
        (
            verts[i][0] + normals[i][0] * xy_compensation_mm,
            verts[i][1] + normals[i][1] * xy_compensation_mm,
            verts[i][2] + normals[i][2] * z_compensation_mm,
        )
        for i in range(len(verts))
    ]


def _unit(vector: Vec3) -> Vec3 | None:
    length = norm(vector)
    if length == 0:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _advance(point: Vec3, direction: Vec3, distance: float) -> Vec3:
    return (
        point[0] + direction[0] * distance,
        point[1] + direction[1] * distance,
        point[2] + direction[2] * distance,
    )


def _open3d_modules():  # pragma: no cover - optional extra
    try:
        import numpy as np
        import open3d as o3d
    except ImportError as exc:
        raise RobustShellUnavailable(
            "robust shell requires the optional 'mesh-processing' extra (Open3D)"
        ) from exc
    return np, o3d
