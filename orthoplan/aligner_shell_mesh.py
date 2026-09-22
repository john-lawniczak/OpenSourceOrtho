from __future__ import annotations

from math import sqrt

from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]


def clean_triangles(triangles: list[Triangle]) -> tuple[list[Triangle], int, int]:
    clean: list[Triangle] = []
    dropped = 0
    skinny = 0
    for tri in triangles:
        welded = tuple(_unkey(_key(vertex)) for vertex in tri)
        if triangle_area(welded) <= 1e-12:
            dropped += 1
            continue
        if _min_altitude(welded) < 1e-4:
            skinny += 1
        clean.append(welded)  # type: ignore[arg-type]
    return _orient_consistently(clean), dropped, skinny


def triangle_area(tri: Triangle) -> float:
    return _norm(_cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0]))) / 2.0


def _key(v: Vec3) -> tuple[int, int, int]:
    return (round(v[0] * 1_000_000), round(v[1] * 1_000_000), round(v[2] * 1_000_000))


def _unkey(key: tuple[int, int, int]) -> Vec3:
    return (key[0] / 1_000_000, key[1] / 1_000_000, key[2] / 1_000_000)


def _min_altitude(tri: Triangle) -> float:
    area2 = triangle_area(tri) * 2
    edges = [_norm(_sub(tri[0], tri[1])), _norm(_sub(tri[1], tri[2])), _norm(_sub(tri[2], tri[0]))]
    longest = max(edges)
    return area2 / longest if longest else 0.0


def _orient_consistently(triangles: list[Triangle]) -> list[Triangle]:
    normal = _normalize(_mean_normal(triangles))
    if normal is None:
        return triangles
    return [_flip_if_needed(tri, normal) for tri in triangles]


def _flip_if_needed(tri: Triangle, normal: Vec3) -> Triangle:
    face_normal = _cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0]))
    return (tri[0], tri[2], tri[1]) if _dot(face_normal, normal) < 0 else tri


def _mean_normal(triangles: list[Triangle]) -> Vec3:
    total = [0.0, 0.0, 0.0]
    for tri in triangles:
        normal = _cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0]))
        total[0] += normal[0]
        total[1] += normal[1]
        total[2] += normal[2]
    return (total[0], total[1], total[2])


def _normalize(vector: Vec3) -> Vec3 | None:
    length = _norm(vector)
    if length == 0:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a: Vec3) -> float:
    return sqrt(_dot(a, a))
