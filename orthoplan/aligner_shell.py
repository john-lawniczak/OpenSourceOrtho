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
    watertight: bool
    triangle_count: int = Field(ge=0)
    trimmed: bool = False


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
    trim: TrimPlane | None = None,
) -> ShellResult:
    """Offset a surface outward by ``thickness_mm`` and close it into a solid."""

    if thickness_mm <= 0:
        raise ValueError("aligner sheet thickness must be positive")
    verts, faces = _index_mesh(triangles)
    if not faces:
        raise ValueError("aligner shell requires a non-empty surface mesh")

    if trim is not None:
        faces = [f for f in faces if all(trim.keeps(verts[i]) for i in f)]
        if not faces:
            raise ValueError("trim removed the entire surface; check the trim plane")

    normals = _vertex_normals(verts, faces)
    outer = [
        (verts[i][0] + normals[i][0] * thickness_mm,
         verts[i][1] + normals[i][1] * thickness_mm,
         verts[i][2] + normals[i][2] * thickness_mm)
        for i in range(len(verts))
    ]

    out: list[Triangle] = []
    for a, b, c in faces:
        # Outer offset surface keeps the original (outward) winding.
        out.append((outer[a], outer[b], outer[c]))
        # Inner cavity surface is the original, reversed so it faces the teeth.
        out.append((verts[a], verts[c], verts[b]))
    # Stitch a rim across every open boundary edge (trim cut + original holes).
    for a, b in _boundary_edges(faces):
        out.append((verts[a], verts[b], outer[b]))
        out.append((verts[a], outer[b], outer[a]))

    return ShellResult(
        triangles=out,
        stats=ShellStats(
            requested_thickness_mm=thickness_mm,
            measured_thickness_mm=_measure_thickness(verts, outer, faces),
            watertight=_is_watertight(out),
            triangle_count=len(out),
            trimmed=trim is not None,
        ),
    )


def _measure_thickness(verts: list[Vec3], outer: list[Vec3], faces: list[tuple[int, int, int]]) -> float:
    """Mean inner→outer displacement over vertices actually used by kept faces."""

    used = {i for f in faces for i in f}
    if not used:
        return 0.0
    total = sum(_norm(_sub(outer[i], verts[i])) for i in used)
    return total / len(used)
