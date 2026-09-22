"""Mesh indexing and topology helpers shared by the aligner-shell builder.

Split from ``aligner_shell`` so the geometry builder stays focused on the offset
and QA flow: this module owns vertex welding/indexing, area-weighted vertex
normals, open-boundary edge detection, and the watertightness test. Pure-Python
and dependency-free.
"""

from __future__ import annotations

from math import sqrt

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a: Vec3) -> float:
    return sqrt(dot(a, a))


def _key(v: Vec3) -> tuple[int, int, int]:
    # Quantize to 1e-6 mm so shared vertices across triangles dedup reliably.
    return (round(v[0] * 1_000_000), round(v[1] * 1_000_000), round(v[2] * 1_000_000))


def index_mesh(triangles: list[Triangle]) -> tuple[list[Vec3], list[tuple[int, int, int]]]:
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


def vertex_normals(verts: list[Vec3], faces: list[tuple[int, int, int]]) -> list[Vec3]:
    acc: list[list[float]] = [[0.0, 0.0, 0.0] for _ in verts]
    for a, b, c in faces:
        # Area-weighted: cross product magnitude is proportional to triangle area.
        n = cross(sub(verts[b], verts[a]), sub(verts[c], verts[a]))
        for i in (a, b, c):
            acc[i][0] += n[0]
            acc[i][1] += n[1]
            acc[i][2] += n[2]
    normals: list[Vec3] = []
    for raw in acc:
        length = norm((raw[0], raw[1], raw[2]))
        if length == 0:
            normals.append((0.0, 0.0, 0.0))
        else:
            normals.append((raw[0] / length, raw[1] / length, raw[2] / length))
    return normals


def boundary_edges(faces: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
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


def is_watertight(triangles: list[Triangle]) -> bool:
    _verts, faces = index_mesh(triangles)
    counts: dict[tuple[int, int], int] = {}
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            undirected = (min(e), max(e))
            counts[undirected] = counts.get(undirected, 0) + 1
    return bool(counts) and all(count == 2 for count in counts.values())
