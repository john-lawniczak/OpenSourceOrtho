"""Optional robust aligner-shell backend (Open3D mesh repair).

Gated behind the optional ``mesh-processing`` extra (Open3D), mirroring the
automatic-registration experiment. The pure-Python backend in ``aligner_shell``
assumes consistent outward winding and offsets along raw vertex normals; this
path first repairs the input mesh with Open3D (merge near-duplicate vertices,
drop degenerate triangles, remove non-manifold edges, orient consistently,
recompute robust normals) and then reuses the shared ``assemble_shell`` offset so
QA stays identical across backends.

It is a repair-first slice, not yet a true boolean/signed-distance offset. When
Open3D is not installed it fails closed (raises ``RobustShellUnavailable``); the
caller falls back to the pure-Python shell and records the downgrade rather than
silently changing geometry.
"""

from __future__ import annotations

from orthoplan.aligner_shell import ShellResult, TrimPlane, assemble_shell

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


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
    verts, faces, dropped, skinny = _repair_mesh(triangles)
    if not faces:
        raise ValueError("aligner shell requires a non-empty surface mesh")
    return assemble_shell(
        verts, faces,
        thickness_mm=thickness_mm,
        minimum_printable_feature_mm=minimum_printable_feature_mm,
        trim=trim,
        xy_compensation_mm=xy_compensation_mm,
        z_compensation_mm=z_compensation_mm,
        dropped=dropped,
        skinny=skinny,
    )


def _repair_mesh(
    triangles: list[Triangle],
) -> tuple[list[Vec3], list[tuple[int, int, int]], int, int]:  # pragma: no cover - optional extra
    """Open3D mesh repair -> (vertices, faces, dropped_count, skinny_count).

    Guarded so the heavy import only happens when the robust path actually runs.
    """

    try:
        import numpy as np
        import open3d as o3d
    except ImportError as exc:
        raise RobustShellUnavailable(
            "robust shell requires the optional 'mesh-processing' extra (Open3D)"
        ) from exc

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
    return verts, faces, dropped, 0
