"""PLY reader (ASCII, binary little-endian, binary big-endian).

PLY is the format Revo Scan and most other structured-light scanners default
to, for both mesh models and raw point clouds. A PLY with no ``face`` element -
or a ``face`` element of count zero - is a point cloud, and is returned as one
rather than being rejected.

Properties beyond x/y/z (normals, colour, confidence, intensity) are skipped:
this engine plans on geometry only.
"""

from __future__ import annotations

import struct

from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    triangulate,
)

_SCALAR = {
    "char": ("b", 1), "int8": ("b", 1),
    "uchar": ("B", 1), "uint8": ("B", 1),
    "short": ("h", 2), "int16": ("h", 2),
    "ushort": ("H", 2), "uint16": ("H", 2),
    "int": ("i", 4), "int32": ("i", 4),
    "uint": ("I", 4), "uint32": ("I", 4),
    "float": ("f", 4), "float32": ("f", 4),
    "double": ("d", 8), "float64": ("d", 8),
}
_FACE_INDEX_NAMES = {"vertex_indices", "vertex_index"}


class _Property:
    __slots__ = ("name", "scalar", "count_type")

    def __init__(self, name: str, scalar: str, count_type: str | None = None) -> None:
        self.name = name
        self.scalar = scalar
        self.count_type = count_type

    @property
    def is_list(self) -> bool:
        return self.count_type is not None


class _Element:
    __slots__ = ("name", "count", "properties")

    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count
        self.properties: list[_Property] = []


def parse(raw: bytes) -> MeshPayload:
    elements, encoding, body = _parse_header(raw)
    if encoding == "ascii":
        points, faces = _read_ascii(elements, body)
    else:
        points, faces = _read_binary(elements, body, big_endian=encoding.endswith("big_endian"))

    notes: list[str] = []
    if not faces:
        notes.append("PLY declares no faces; treated as a point cloud")
    label = "ply-ascii" if encoding == "ascii" else f"ply-{'be' if encoding.endswith('big_endian') else 'le'}"
    if not faces:
        label = f"{label}-points"
    return MeshPayload(points=points, faces=faces, source_format=label, notes=notes)


def _parse_header(raw: bytes) -> tuple[list[_Element], str, bytes]:
    marker = b"end_header"
    cut = raw.find(marker)
    if not raw.lstrip().startswith(b"ply") or cut < 0:
        raise MeshParseError("PLY header is missing or malformed")
    line_end = raw.find(b"\n", cut)
    header = raw[:cut].decode("ascii", errors="replace")
    body = raw[line_end + 1:] if line_end >= 0 else b""

    encoding = ""
    elements: list[_Element] = []
    for line in header.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format" and len(parts) >= 2:
            encoding = parts[1]
        elif parts[0] == "element" and len(parts) >= 3:
            elements.append(_Element(parts[1], int(parts[2])))
        elif parts[0] == "property" and elements:
            elements[-1].properties.append(_property_from(parts))
    if encoding not in {"ascii", "binary_little_endian", "binary_big_endian"}:
        raise MeshParseError(f"unsupported PLY format: {encoding or 'unspecified'!r}")
    if not any(element.name == "vertex" for element in elements):
        raise MeshParseError("PLY declares no vertex element")
    return elements, encoding, body


def _property_from(parts: list[str]) -> _Property:
    if parts[1] == "list" and len(parts) >= 5:
        return _Property(parts[4], parts[3], count_type=parts[2])
    if len(parts) >= 3:
        return _Property(parts[2], parts[1])
    raise MeshParseError(f"malformed PLY property: {' '.join(parts)}")


def _vertex_axes(element: _Element) -> tuple[int, int, int]:
    names = [prop.name for prop in element.properties]
    try:
        return names.index("x"), names.index("y"), names.index("z")
    except ValueError as exc:
        raise MeshParseError("PLY vertex element has no x/y/z properties") from exc


def _read_ascii(elements: list[_Element], body: bytes) -> tuple[list[Vec3], list[Face]]:
    tokens = body.decode("utf-8", errors="replace").split()
    cursor = 0
    points: list[Vec3] = []
    faces: list[Face] = []
    for element in elements:
        axes = _vertex_axes(element) if element.name == "vertex" else None
        for _ in range(element.count):
            values: list[list[float]] = []
            for prop in element.properties:
                if prop.is_list:
                    length = int(float(tokens[cursor]))
                    cursor += 1
                    values.append([float(token) for token in tokens[cursor:cursor + length]])
                    cursor += length
                else:
                    values.append([float(tokens[cursor])])
                    cursor += 1
            _collect(element, axes, values, points, faces)
    return points, faces


def _read_binary(
    elements: list[_Element], body: bytes, *, big_endian: bool
) -> tuple[list[Vec3], list[Face]]:
    order = ">" if big_endian else "<"
    offset = 0
    points: list[Vec3] = []
    faces: list[Face] = []
    for element in elements:
        axes = _vertex_axes(element) if element.name == "vertex" else None
        for _ in range(element.count):
            values: list[list[float]] = []
            for prop in element.properties:
                if prop.is_list:
                    length, offset = _scalar(body, offset, prop.count_type or "uchar", order)
                    entries: list[float] = []
                    for _index in range(int(length)):
                        value, offset = _scalar(body, offset, prop.scalar, order)
                        entries.append(value)
                    values.append(entries)
                else:
                    value, offset = _scalar(body, offset, prop.scalar, order)
                    values.append([value])
            _collect(element, axes, values, points, faces)
    return points, faces


def _scalar(body: bytes, offset: int, scalar: str, order: str) -> tuple[float, int]:
    code = _SCALAR.get(scalar)
    if code is None:
        raise MeshParseError(f"unsupported PLY property type: {scalar!r}")
    symbol, size = code
    if offset + size > len(body):
        raise MeshParseError("PLY body ended before the declared elements were read")
    (value,) = struct.unpack_from(f"{order}{symbol}", body, offset)
    return float(value), offset + size


def _collect(
    element: _Element,
    axes: tuple[int, int, int] | None,
    values: list[list[float]],
    points: list[Vec3],
    faces: list[Face],
) -> None:
    if element.name == "vertex" and axes is not None:
        points.append((values[axes[0]][0], values[axes[1]][0], values[axes[2]][0]))
        return
    if element.name != "face":
        return
    for prop, entry in zip(element.properties, values):
        if prop.is_list and prop.name in _FACE_INDEX_NAMES:
            faces.extend(triangulate([int(index) for index in entry]))
            return
