"""Aligner-shell geometry: turn a per-stage tooth surface into a printable shell.

This is the manufacturing step that makes a stage *model* into a 3D-printable
aligner *shell*: the reviewed tooth surface is offset outward along vertex normals
by the aligner sheet thickness, optionally trimmed along a gingival plane, and
closed into a watertight solid (outer offset surface + inner cavity surface +
stitched rim). The plastic occupies the gap between the inner (tooth-facing) and
outer (offset) surfaces.

Pure-Python and dependency-free so it always runs; it assumes the input surface
has consistent outward winding (reviewed segmented crowns do). A robust path that
repairs winding and does true mesh offset/booleans belongs behind the optional
``mesh-processing`` extra. Generating this geometry is NOT a clinical claim:
printing, fit, materials, and physical use remain the user's own responsibility
and risk.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.aligner_shell_quality import (
    count_nonmanifold_edges,
    count_self_intersections,
    min_inner_outer_clearance,
)
from orthoplan.aligner_shell_mesh import clean_triangles
from orthoplan.aligner_shell_stats import connected_components, mean, percentile
from orthoplan.aligner_shell_topology import (
    boundary_edges,
    dot,
    index_mesh,
    is_watertight,
    norm,
    sub,
    vertex_normals,
)

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


class TrimPlane(BaseModel):
    """Keep geometry on the +normal side of point; cut the rest (gingival trim)."""

    point: Vec3
    normal: Vec3

    def keeps(self, vertex: Vec3) -> bool:
        return dot(sub(vertex, self.point), self.normal) >= 0.0


class ShellStats(BaseModel):
    requested_thickness_mm: float
    measured_thickness_mm: float
    min_thickness_mm: float
    max_thickness_mm: float
    p05_thickness_mm: float
    p50_thickness_mm: float
    p95_thickness_mm: float
    watertight: bool
    connected_components: int = Field(ge=0)
    dropped_degenerate_input_triangles: int = Field(ge=0)
    skinny_input_triangle_count: int = Field(ge=0)
    input_boundary_edge_count: int = Field(ge=0)
    stitched_rim_triangle_count: int = Field(ge=0)
    rim_closed: bool
    self_intersection_count: int = Field(ge=0)
    nonmanifold_edge_count: int = Field(ge=0)
    inner_outer_min_clearance_mm: float
    minimum_printable_feature_mm: float
    triangle_count: int = Field(ge=0)
    trimmed: bool = False
    xy_compensation_mm: float = 0.0
    z_compensation_mm: float = 0.0


class ShellResult(BaseModel):
    triangles: list[Triangle]
    stats: ShellStats


def build_aligner_shell(
    triangles: list[Triangle],
    *,
    thickness_mm: float,
    minimum_printable_feature_mm: float = 0.3,
    trim: TrimPlane | None = None,
    xy_compensation_mm: float = 0.0,
    z_compensation_mm: float = 0.0,
) -> ShellResult:
    """Offset a surface outward by ``thickness_mm`` and close it into a solid.

    ``xy_compensation_mm`` / ``z_compensation_mm`` apply the printer's dimensional
    compensation directly to the exported geometry (see ``_shell_surfaces``) so the
    STL contains the part the manifest advertises, not just the metadata.
    """

    if thickness_mm <= 0:
        raise ValueError("aligner sheet thickness must be positive")
    cleaned, dropped, skinny = clean_triangles(triangles)
    verts, faces = index_mesh(cleaned)
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


def assemble_shell(
    verts: list[Vec3],
    faces: list[tuple[int, int, int]],
    *,
    thickness_mm: float,
    minimum_printable_feature_mm: float,
    trim: TrimPlane | None,
    xy_compensation_mm: float,
    z_compensation_mm: float,
    dropped: int,
    skinny: int,
) -> ShellResult:
    """Offset already-indexed geometry and close it into a solid.

    Shared by every backend (pure-Python ``clean_triangles`` and the optional
    robust repair path) so offset, rim stitching, compensation, and QA have a
    single source of truth regardless of how the input mesh was prepared.
    """

    if trim is not None:
        faces = [f for f in faces if all(trim.keeps(verts[i]) for i in f)]
        if not faces:
            raise ValueError("trim removed the entire surface; check the trim plane")

    input_boundary_edges = boundary_edges(faces)
    normals = vertex_normals(verts, faces)
    inner, outer = _shell_surfaces(
        verts, normals, thickness_mm, xy_compensation_mm, z_compensation_mm
    )

    out: list[Triangle] = []
    for a, b, c in faces:
        # Outer offset surface keeps the original (outward) winding.
        out.append((outer[a], outer[b], outer[c]))
        # Inner cavity surface is the original, reversed so it faces the teeth.
        out.append((inner[a], inner[c], inner[b]))
    # Stitch a rim across every open boundary edge (trim cut + original holes).
    for a, b in input_boundary_edges:
        out.append((inner[a], inner[b], outer[b]))
        out.append((inner[a], outer[b], outer[a]))

    return ShellResult(
        triangles=out,
        stats=_shell_stats(
            inner, outer, faces, out, input_boundary_edges,
            dropped, skinny, thickness_mm, minimum_printable_feature_mm, trim is not None,
            xy_compensation_mm, z_compensation_mm,
        ),
    )


def _shell_surfaces(
    verts: list[Vec3],
    normals: list[Vec3],
    thickness_mm: float,
    xy_compensation_mm: float,
    z_compensation_mm: float,
) -> tuple[list[Vec3], list[Vec3]]:
    """Inner (tooth-facing) and outer (offset) surface points.

    The printer compensation bias is added to BOTH surfaces (XY gain in-plane, Z
    gain on the build axis), shifting outer dimensions without altering the
    inner-to-outer wall thickness.
    """

    inner = [
        (verts[i][0] + normals[i][0] * xy_compensation_mm,
         verts[i][1] + normals[i][1] * xy_compensation_mm,
         verts[i][2] + normals[i][2] * z_compensation_mm)
        for i in range(len(verts))
    ]
    outer = [
        (inner[i][0] + normals[i][0] * thickness_mm,
         inner[i][1] + normals[i][1] * thickness_mm,
         inner[i][2] + normals[i][2] * thickness_mm)
        for i in range(len(verts))
    ]
    return inner, outer


def _shell_stats(
    inner: list[Vec3],
    outer: list[Vec3],
    faces: list[tuple[int, int, int]],
    shell_triangles: list[Triangle],
    input_boundary_edges: list[tuple[int, int]],
    dropped: int,
    skinny: int,
    thickness_mm: float,
    minimum_printable_feature_mm: float,
    trimmed: bool,
    xy_compensation_mm: float,
    z_compensation_mm: float,
) -> ShellStats:
    thicknesses = _thickness_values(inner, outer, faces)
    _, shell_faces = index_mesh(shell_triangles)
    watertight = is_watertight(shell_triangles)
    rim_triangles = len(input_boundary_edges) * 2
    return ShellStats(
        requested_thickness_mm=thickness_mm,
        measured_thickness_mm=mean(thicknesses),
        min_thickness_mm=min(thicknesses),
        max_thickness_mm=max(thicknesses),
        p05_thickness_mm=percentile(thicknesses, 0.05),
        p50_thickness_mm=percentile(thicknesses, 0.50),
        p95_thickness_mm=percentile(thicknesses, 0.95),
        watertight=watertight,
        connected_components=connected_components(shell_faces),
        dropped_degenerate_input_triangles=dropped,
        skinny_input_triangle_count=skinny,
        input_boundary_edge_count=len(input_boundary_edges),
        stitched_rim_triangle_count=rim_triangles,
        rim_closed=watertight and rim_triangles == len(input_boundary_edges) * 2,
        self_intersection_count=count_self_intersections(shell_triangles),
        nonmanifold_edge_count=count_nonmanifold_edges(shell_triangles),
        inner_outer_min_clearance_mm=min_inner_outer_clearance(inner, outer),
        minimum_printable_feature_mm=minimum_printable_feature_mm,
        triangle_count=len(shell_triangles),
        trimmed=trimmed,
        xy_compensation_mm=xy_compensation_mm,
        z_compensation_mm=z_compensation_mm,
    )


def _thickness_values(
    inner: list[Vec3], outer: list[Vec3], faces: list[tuple[int, int, int]]
) -> list[float]:
    """Inner-to-outer displacement samples over vertices used by kept faces."""

    used = {i for f in faces for i in f}
    if not used:
        return [0.0]
    return [norm(sub(outer[i], inner[i])) for i in sorted(used)]
