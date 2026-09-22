"""FBX reader (binary and ASCII).

Revo Scan exports FBX for mesh and textured models. Only the geometry records
are read: ``Vertices`` (a flat x,y,z stream) and ``PolygonVertexIndex`` (flat
polygon corners where a negative value, decoded as ``-value - 1``, marks the
last corner of a polygon). Materials, textures, deformers, and animation
records are ignored.

FBX stores an explicit ``UnitScaleFactor`` relative to centimetres, which is
reported as a declared unit for the user to confirm - never applied silently.
"""

from __future__ import annotations

import re

from orthoplan.io.mesh_formats import fbx_binary
from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    triangulate,
)

_ASCII_MARKER = "FBXHeaderExtension"
# UnitScaleFactor is a multiplier from centimetres to the file's system unit.
_UNIT_BY_SCALE = {0.1: "millimeter", 1.0: "centimeter", 2.54: "inch", 100.0: "meter"}
_ASCII_ARRAY = re.compile(
    r"(Vertices|PolygonVertexIndex)\s*:\s*\*?\d*\s*\{\s*a\s*:\s*([^}]*)\}",
    re.IGNORECASE,
)


def parse(raw: bytes) -> MeshPayload:
    if fbx_binary.is_binary_fbx(raw):
        meshes, unit_scale, label = _from_binary(raw), _binary_unit_scale(raw), "fbx-binary"
    else:
        meshes, unit_scale, label = _from_ascii(raw), _ascii_unit_scale(raw), "fbx-ascii"

    points: list[Vec3] = []
    faces: list[Face] = []
    for vertices, polygon_indices in meshes:
        _append_mesh(vertices, polygon_indices, points, faces)

    notes: list[str] = []
    declared = _UNIT_BY_SCALE.get(round(unit_scale, 4)) if unit_scale else None
    if unit_scale and declared is None:
        notes.append(
            f"FBX declares UnitScaleFactor {unit_scale:g}, which maps to no standard unit; "
            "confirm scan scale manually"
        )
    if not faces:
        notes.append("FBX declares no polygons; treated as a point cloud")
        label = f"{label}-points"
    return MeshPayload(
        points=points, faces=faces, source_format=label,
        declared_units=declared, notes=notes,
    )


def _append_mesh(
    vertices: list[float], polygon_indices: list[int], points: list[Vec3], faces: list[Face]
) -> None:
    if len(vertices) % 3:
        raise MeshParseError("FBX Vertices array length is not a multiple of 3")
    base = len(points)
    vertex_count = len(vertices) // 3
    points.extend(
        (vertices[index * 3], vertices[index * 3 + 1], vertices[index * 3 + 2])
        for index in range(vertex_count)
    )

    polygon: list[int] = []
    for raw_index in polygon_indices:
        closing = raw_index < 0
        index = -raw_index - 1 if closing else raw_index
        if index < 0 or index >= vertex_count:
            raise MeshParseError("FBX polygon references a vertex outside the Vertices array")
        polygon.append(base + index)
        if closing:
            faces.extend(triangulate(polygon))
            polygon = []
    if polygon:
        faces.extend(triangulate(polygon))


def _from_binary(raw: bytes) -> list[tuple[list[float], list[int]]]:
    """Vertex/polygon array pairs, one per Geometry record, in document order."""

    meshes: list[tuple[list[float], list[int]]] = []
    pending: list[float] | None = None
    for name, properties in fbx_binary.read_records(raw):
        values = properties[0] if properties and isinstance(properties[0], list) else None
        if values is None:
            continue
        if name == "Vertices":
            if pending is not None:
                meshes.append((pending, []))
            pending = [float(value) for value in values]
        elif name == "PolygonVertexIndex" and pending is not None:
            meshes.append((pending, [int(value) for value in values]))
            pending = None
    if pending is not None:
        meshes.append((pending, []))
    if not meshes:
        raise MeshParseError("FBX file contains no Geometry vertices")
    return meshes


def _from_ascii(raw: bytes) -> list[tuple[list[float], list[int]]]:
    text = raw.decode("utf-8", errors="replace")
    if _ASCII_MARKER not in text:
        raise MeshParseError("file is neither a binary nor a recognisable ASCII FBX")
    meshes: list[tuple[list[float], list[int]]] = []
    pending: list[float] | None = None
    for match in _ASCII_ARRAY.finditer(text):
        values = _numbers(match.group(2))
        if match.group(1).lower() == "vertices":
            if pending is not None:
                meshes.append((pending, []))
            pending = values
        elif pending is not None:
            meshes.append((pending, [int(value) for value in values]))
            pending = None
    if pending is not None:
        meshes.append((pending, []))
    if not meshes:
        raise MeshParseError("FBX file contains no Geometry vertices")
    return meshes


def _numbers(block: str) -> list[float]:
    try:
        return [float(token) for token in block.replace("\n", " ").split(",") if token.strip()]
    except ValueError as exc:
        raise MeshParseError("FBX array contains a non-numeric value") from exc


def _binary_unit_scale(raw: bytes) -> float | None:
    for name, properties in fbx_binary.read_records(raw):
        if name == "P" and properties and properties[0] == "UnitScaleFactor":
            numeric = [value for value in properties[1:] if isinstance(value, (int, float))]
            if numeric:
                return float(numeric[-1])
    return None


def _ascii_unit_scale(raw: bytes) -> float | None:
    match = re.search(
        r'"UnitScaleFactor"[^\n]*?,\s*([-\d.eE+]+)\s*$',
        raw.decode("utf-8", errors="replace"),
        re.MULTILINE,
    )
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
