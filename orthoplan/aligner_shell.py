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

from math import sqrt

from pydantic import BaseModel, Field

from orthoplan.aligner_shell_quality import (
    min_inner_outer_clearance,
    triangle_aabb_intersection_count,
)
from orthoplan.aligner_shell_mesh import clean_triangles
from orthoplan.aligner_shell_stats import connected_components, mean, percentile

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


class TrimPlane(BaseModel):
    """Keep geometry on the +normal side of point; cut the rest (gingival trim)."""

    point: Vec3
    normal: Vec3

    def keeps(self, vertex: Vec3) -> bool:
        return _dot(_sub(vertex, self.point), self.normal) >= 0.0


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
    inner_outer_min_clearance_mm: float
    minimum_printable_feature_mm: float
    triangle_count: int = Field(ge=0)
    trimmed: bool = False
    xy_compensation_mm: float = 0.0
    z_compensation_mm: float = 0.0


class ShellResult(BaseModel):
    triangles: list[Triangle]
    stats: ShellStats


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a: Vec3) -> float:
    return sqrt(_dot(a, a))


def _key(v: Vec3) -> tuple[int, int, int]:
    # Quantize to 1e-6 mm so shared vertices across triangles dedup reliably.
    return (round(v[0] * 1_000_000), round(v[1] * 1_000_000), round(v[2] * 1_000_000))


def _index_mesh(triangles: list[Triangle]) -> tuple[list[Vec3], list[tuple[int, int, int]]]:
    verts: list[Vec3] = []
    lookup: dict[tuple[int, int, int], int] = {}
    faces: list[tuple[int, int, int]] = []
    for tri in triangles:
        idx = []
        for v in tri:
            k = _key(v)
            i = lookup.get(k)
            if i is None:
                i = len(verts)
                lookup[k] = i
                verts.append(v)
            idx.append(i)
        if idx[0] != idx[1] and idx[1] != idx[2] and idx[0] != idx[2]:
            faces.append((idx[0], idx[1], idx[2]))
    return verts, faces


def _vertex_normals(verts: list[Vec3], faces: list[tuple[int, int, int]]) -> list[Vec3]:
    acc: list[list[float]] = [[0.0, 0.0, 0.0] for _ in verts]
    for a, b, c in faces:
        # Area-weighted: cross product magnitude is proportional to triangle area.
        n = _cross(_sub(verts[b], verts[a]), _sub(verts[c], verts[a]))
        for i in (a, b, c):
            acc[i][0] += n[0]
            acc[i][1] += n[1]
            acc[i][2] += n[2]
    normals: list[Vec3] = []
    for raw in acc:
        length = _norm((raw[0], raw[1], raw[2]))
        if length == 0:
            normals.append((0.0, 0.0, 0.0))
        else:
            normals.append((raw[0] / length, raw[1] / length, raw[2] / length))
    return normals


def _boundary_edges(faces: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    """Directed edges that appear in exactly one triangle - the open boundary."""

    counts: dict[tuple[int, int], int] = {}
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            undirected = (min(e), max(e))
            counts[undirected] = counts.get(undirected, 0) + 1
    boundary: list[tuple[int, int]] = []
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            if counts[(min(e), max(e))] == 1:
                boundary.append(e)
    return boundary


def _is_watertight(triangles: list[Triangle]) -> bool:
    verts, faces = _index_mesh(triangles)
    counts: dict[tuple[int, int], int] = {}
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            undirected = (min(e), max(e))
            counts[undirected] = counts.get(undirected, 0) + 1
    return bool(counts) and all(count == 2 for count in counts.values())


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
    compensation directly to the exported geometry: every surface point is biased
    along its vertex normal (XY gain in-plane, Z gain along the build axis). The
    bias is applied equally to the inner cavity and outer surfaces, so it shifts
    the part's outer dimensions to cancel printer over/under-cure WITHOUT changing
    wall thickness. Reporting these values in a manifest while leaving the mesh
    uncompensated would describe a part the STL does not contain, so the
    compensation must live in the vertices, not only the metadata.
    """

    if thickness_mm <= 0:
        raise ValueError("aligner sheet thickness must be positive")
    cleaned, dropped, skinny = clean_triangles(triangles)
    verts, faces = _index_mesh(cleaned)
    if not faces:
        raise ValueError("aligner shell requires a non-empty surface mesh")

    if trim is not None:
        faces = [f for f in faces if all(trim.keeps(verts[i]) for i in f)]
        if not faces:
            raise ValueError("trim removed the entire surface; check the trim plane")

    input_boundary_edges = _boundary_edges(faces)
    normals = _vertex_normals(verts, faces)
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
    _, shell_faces = _index_mesh(shell_triangles)
    watertight = _is_watertight(shell_triangles)
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
        self_intersection_count=triangle_aabb_intersection_count(shell_triangles),
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
    return [_norm(_sub(outer[i], inner[i])) for i in sorted(used)]
