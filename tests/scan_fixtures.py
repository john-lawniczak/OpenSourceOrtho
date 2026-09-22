"""Tiny one- and two-triangle scans, written in every supported format.

Each builder returns the bytes of the SAME unit tetrahedron face set, so a test
can assert that a format round-trips to the same geometry rather than merely
parsing without raising.
"""

from __future__ import annotations

import base64
import json
import struct
import zipfile
from io import BytesIO

POINTS = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)]
FACES = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]


def triangles() -> list[tuple[tuple[float, float, float], ...]]:
    return [(POINTS[a], POINTS[b], POINTS[c]) for a, b, c in FACES]


def stl_ascii() -> bytes:
    lines = ["solid t"]
    for tri in triangles():
        lines += ["  facet normal 0 0 1", "    outer loop"]
        lines += [f"      vertex {v[0]} {v[1]} {v[2]}" for v in tri]
        lines += ["    endloop", "  endfacet"]
    lines.append("endsolid t")
    return ("\n".join(lines) + "\n").encode()


def ply_ascii(*, with_faces: bool = True) -> bytes:
    head = ["ply", "format ascii 1.0", f"element vertex {len(POINTS)}"]
    head += ["property float x", "property float y", "property float z"]
    if with_faces:
        head += [f"element face {len(FACES)}", "property list uchar int vertex_indices"]
    head.append("end_header")
    rows = [f"{x} {y} {z}" for x, y, z in POINTS]
    if with_faces:
        rows += [f"3 {a} {b} {c}" for a, b, c in FACES]
    return ("\n".join(head + rows) + "\n").encode()


def ply_binary(*, big_endian: bool = False) -> bytes:
    order = ">" if big_endian else "<"
    head = (
        "ply\n"
        f"format binary_{'big' if big_endian else 'little'}_endian 1.0\n"
        f"element vertex {len(POINTS)}\n"
        "property float x\nproperty float y\nproperty float z\nproperty uchar red\n"
        f"element face {len(FACES)}\n"
        "property list uchar int vertex_indices\nend_header\n"
    ).encode()
    body = b"".join(struct.pack(f"{order}3fB", x, y, z, 7) for x, y, z in POINTS)
    body += b"".join(struct.pack(f"{order}B3i", 3, a, b, c) for a, b, c in FACES)
    return head + body


def obj(*, with_faces: bool = True) -> bytes:
    lines = ["# fixture", "mtllib ignored.mtl"]
    lines += [f"v {x} {y} {z}" for x, y, z in POINTS]
    if with_faces:
        lines += [f"f {a + 1}/1/1 {b + 1}/2/2 {c + 1}/3/3" for a, b, c in FACES]
    return ("\n".join(lines) + "\n").encode()


def asc_points() -> bytes:
    rows = ["# Revo Scan export", "10.0 0.0 0.0 0.1 0.2 0.3"]
    rows += [f"{x},{y},{z}" for x, y, z in POINTS]
    return ("\n".join(rows) + "\n").encode()


def three_mf(*, unit: str = "millimeter") -> bytes:
    vertices = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in POINTS)
    faces = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in FACES)
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<resources><object id="1" type="model"><mesh>'
        f"<vertices>{vertices}</vertices><triangles>{faces}</triangles>"
        "</mesh></object></resources>"
        '<build><item objectid="1"/></build></model>'
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("3D/3dmodel.model", model)
    return buffer.getvalue()


def _gltf_buffer() -> tuple[bytes, int]:
    positions = b"".join(struct.pack("<3f", *point) for point in POINTS)
    indices = b"".join(struct.pack("<H", index) for face in FACES for index in face)
    padding = b"\x00" * (-len(positions) % 4)
    return positions + padding + indices, len(positions + padding)


def _gltf_document(index_offset: int, total: int, uri: str | None = None) -> dict:
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(POINTS), "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": len(FACES) * 3, "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": index_offset},
            {"buffer": 0, "byteOffset": index_offset, "byteLength": total - index_offset},
        ],
        "buffers": [{"byteLength": total}],
    }
    if uri:
        document["buffers"][0]["uri"] = uri
    return document


def gltf(*, uri: str | None = None, scale: float = 1.0) -> bytes:
    data, offset = _gltf_buffer()
    embedded = uri or (
        "data:application/octet-stream;base64," + base64.b64encode(data).decode()
    )
    document = _gltf_document(offset, len(data), embedded)
    if scale != 1.0:
        document["nodes"][0]["scale"] = [scale, scale, scale]
    return json.dumps(document).encode()


def gltf_sidecar_buffer() -> bytes:
    return _gltf_buffer()[0]


def glb() -> bytes:
    data, offset = _gltf_buffer()
    document = json.dumps(_gltf_document(offset, len(data))).encode()
    document += b" " * (-len(document) % 4)
    binary = data + b"\x00" * (-len(data) % 4)
    total = 12 + 8 + len(document) + 8 + len(binary)
    out = struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<II", len(document), 0x4E4F534A) + document
    out += struct.pack("<II", len(binary), 0x004E4942) + binary
    return out


def fbx_ascii(*, unit_scale: float = 0.1) -> bytes:
    vertices = ",".join(str(value) for point in POINTS for value in point)
    polygons = ",".join(
        str(value) for face in FACES for value in (face[0], face[1], -face[2] - 1)
    )
    return (
        "; FBX 7.4.0 fixture\n"
        "FBXHeaderExtension:  {\n    FBXHeaderVersion: 1003\n}\n"
        "GlobalSettings:  {\n    Properties70:  {\n"
        f'        P: "UnitScaleFactor", "double", "Number", "",{unit_scale}\n'
        "    }\n}\n"
        'Objects:  {\n    Geometry: 1, "Geometry::t", "Mesh" {\n'
        f"        Vertices: *{len(POINTS) * 3} {{\n            a: {vertices}\n        }}\n"
        f"        PolygonVertexIndex: *{len(FACES) * 3} {{\n            a: {polygons}\n        }}\n"
        "    }\n}\n"
    ).encode()


def fbx_binary(*, compressed: bool = False) -> bytes:
    import zlib

    def array(code: bytes, symbol: str, values: list) -> bytes:
        payload = struct.pack(f"<{len(values)}{symbol}", *values)
        if compressed:
            deflated = zlib.compress(payload)
            return code + struct.pack("<III", len(values), 1, len(deflated)) + deflated
        return code + struct.pack("<III", len(values), 0, len(payload)) + payload

    vertices = [value for point in POINTS for value in point]
    polygons = [value for face in FACES for value in (face[0], face[1], -face[2] - 1)]

    def record(name: bytes, properties: bytes, count: int, children: list, start: int):
        header = 13 + len(name)
        body = b""
        cursor = start + header + len(properties)
        for child in children:
            blob, cursor = record(*child, cursor)
            body += blob
        if children:
            body += b"\x00" * 13
            cursor += 13
        head = struct.pack("<III", cursor, count, len(properties)) + bytes([len(name)]) + name
        return head + properties + body, cursor

    out = bytearray(b"Kaydara FBX Binary  \x00\x1a\x00" + struct.pack("<I", 7400))
    geometry = [
        (b"Vertices", array(b"d", "d", vertices), 1, []),
        (b"PolygonVertexIndex", array(b"i", "i", [int(v) for v in polygons]), 1, []),
    ]
    blob, _end = record(b"Objects", b"", 0, [(b"Geometry", b"", 0, geometry)], len(out))
    out += blob + b"\x00" * 13
    return bytes(out)
