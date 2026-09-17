"""STL reader (binary and ASCII).

STL stores a bare triangle soup: no vertex sharing, no units, no colour. Each
facet is emitted as three fresh points so the returned payload matches the file
exactly rather than a de-duplicated reconstruction of it.
"""

from __future__ import annotations

import struct

from orthoplan.io.mesh_formats.payload import MeshParseError, MeshPayload, Vec3


def looks_binary(raw: bytes) -> bool:
    if len(raw) < 84:
        return False
    (count,) = struct.unpack_from("<I", raw, 80)
    return len(raw) == 84 + count * 50


def parse(raw: bytes) -> MeshPayload:
    if looks_binary(raw):
        facets, points = _read_binary(raw)
        source_format = "stl-binary"
    else:
        facets, points = _read_ascii(raw)
        source_format = "stl-ascii"

    if facets <= 0 or not points:
        raise MeshParseError("STL contains no readable facets or vertices")
    if len(points) != facets * 3:
        raise MeshParseError("STL facet and vertex counts are inconsistent")

    faces = [(index, index + 1, index + 2) for index in range(0, len(points), 3)]
    return MeshPayload(points=points, faces=faces, source_format=source_format)


def _read_binary(raw: bytes) -> tuple[int, list[Vec3]]:
    (count,) = struct.unpack_from("<I", raw, 80)
    points: list[Vec3] = []
    offset = 84
    for _ in range(count):
        # 12 floats per facet: normal(3) + v0(3) + v1(3) + v2(3); skip normal.
        values = struct.unpack_from("<12f", raw, offset)
        points.extend((values[3:6], values[6:9], values[9:12]))
        offset += 50
    return count, points


def _read_ascii(raw: bytes) -> tuple[int, list[Vec3]]:
    text = raw.decode("utf-8", errors="replace")
    points: list[Vec3] = []
    facets = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("facet normal"):
            facets += 1
        elif stripped.startswith("vertex"):
            parts = stripped.split()
            if len(parts) != 4 or parts[0] != "vertex":
                raise MeshParseError(f"invalid STL vertex on line {line_number}")
            try:
                points.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError as exc:
                raise MeshParseError(f"invalid STL vertex on line {line_number}") from exc
    return facets, points
