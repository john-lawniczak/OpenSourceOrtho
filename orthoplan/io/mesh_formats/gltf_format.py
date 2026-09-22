"""glTF 2.0 and GLB reader.

Revo Scan exports GLTF for mesh and textured models. Both the JSON (``.gltf``)
and binary-container (``.glb``) flavours are read here; buffers arrive either
embedded in the GLB chunk, as a base64 ``data:`` URI, or as a sibling ``.bin``
file next to the ``.gltf``.

Only ``POSITION`` and ``indices`` are read - materials, textures, animation,
skins, and morph targets are irrelevant to planning geometry. glTF is specified
in metres, which is reported as a declared unit but never applied silently.
"""

from __future__ import annotations

import base64
import json
import struct
import urllib.parse
from pathlib import Path

from orthoplan.io.mesh_formats import gltf_matrix as mat
from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    triangulate,
)

_GLB_MAGIC = b"glTF"
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942
_COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_TRIANGLES_MODE = 4


def parse(raw: bytes, *, path: Path | None = None) -> MeshPayload:
    if raw[:4] == _GLB_MAGIC:
        document, embedded = _split_glb(raw)
        source_format = "glb"
    else:
        try:
            document = json.loads(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MeshParseError("glTF file is not valid JSON") from exc
        embedded = None
        source_format = "gltf"
    if not isinstance(document, dict):
        raise MeshParseError("glTF root must be a JSON object")

    buffers = _load_buffers(document, embedded, path)
    points: list[Vec3] = []
    faces: list[Face] = []
    notes: list[str] = []
    for mesh_index, transform in _mesh_instances(document):
        _read_mesh(document, buffers, mesh_index, transform, points, faces, notes)

    if not faces:
        notes.append("glTF declares no triangles; treated as a point cloud")
        source_format = f"{source_format}-points"
    return MeshPayload(
        points=points,
        faces=faces,
        source_format=source_format,
        declared_units="meter",
        notes=sorted(set(notes)),
    )


def _split_glb(raw: bytes) -> tuple[dict, bytes | None]:
    if len(raw) < 12:
        raise MeshParseError("GLB file is truncated")
    document: dict | None = None
    binary: bytes | None = None
    offset = 12
    while offset + 8 <= len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        payload = raw[offset + 8: offset + 8 + length]
        if kind == _CHUNK_JSON and document is None:
            document = json.loads(payload.decode("utf-8", errors="replace").rstrip("\x00 "))
        elif kind == _CHUNK_BIN and binary is None:
            binary = payload
        offset += 8 + length + (-length % 4)
    if document is None:
        raise MeshParseError("GLB container has no JSON chunk")
    return document, binary


def _load_buffers(document: dict, embedded: bytes | None, path: Path | None) -> list[bytes]:
    buffers: list[bytes] = []
    for index, buffer in enumerate(document.get("buffers") or []):
        uri = buffer.get("uri") if isinstance(buffer, dict) else None
        if not uri:
            buffers.append(embedded or b"")
        elif uri.startswith("data:"):
            _, _, encoded = uri.partition(",")
            buffers.append(base64.b64decode(encoded + "=" * (-len(encoded) % 4)))
        else:
            buffers.append(_sidecar_bytes(uri, path, index))
    return buffers


def _sidecar_bytes(uri: str, path: Path | None, index: int) -> bytes:
    """Read an external buffer, refusing anything outside the file's directory."""

    if path is None:
        raise MeshParseError(
            f"glTF buffer {index} points at an external file, which needs the .gltf on disk"
        )
    relative = urllib.parse.unquote(uri)
    if relative.startswith(("http://", "https://", "//", "/")) or ":" in relative.split("/")[0]:
        raise MeshParseError(f"glTF buffer {index} points at a remote URI, which is not fetched")
    root = path.parent.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise MeshParseError(f"glTF buffer {index} ({relative!r}) is missing next to the .gltf file")
    return candidate.read_bytes()


def _mesh_instances(document: dict) -> list[tuple[int, mat.Matrix]]:
    """Every mesh to read, paired with the world transform that places it."""

    nodes = document.get("nodes") or []
    scenes = document.get("scenes") or []
    scene_index = document.get("scene", 0)
    roots: list[int] = []
    if isinstance(scenes, list) and 0 <= scene_index < len(scenes):
        roots = [index for index in (scenes[scene_index].get("nodes") or []) if isinstance(index, int)]

    instances: list[tuple[int, mat.Matrix]] = []
    if roots:
        seen: set[int] = set()
        for root in roots:
            _walk(nodes, root, mat.IDENTITY, instances, seen)
    if not instances:
        # No scene graph (or an empty one): read the meshes as authored.
        instances = [(index, mat.IDENTITY) for index in range(len(document.get("meshes") or []))]
    return instances


def _walk(
    nodes: list, index: int, parent: mat.Matrix,
    instances: list[tuple[int, mat.Matrix]], seen: set[int],
) -> None:
    if index in seen or not (0 <= index < len(nodes)) or not isinstance(nodes[index], dict):
        return
    seen.add(index)
    node = nodes[index]
    world = mat.multiply(parent, mat.from_node(node))
    if isinstance(node.get("mesh"), int):
        instances.append((node["mesh"], world))
    for child in node.get("children") or []:
        if isinstance(child, int):
            _walk(nodes, child, world, instances, seen)


def _read_mesh(
    document: dict, buffers: list[bytes], mesh_index: int, transform: mat.Matrix,
    points: list[Vec3], faces: list[Face], notes: list[str],
) -> None:
    meshes = document.get("meshes") or []
    if not (0 <= mesh_index < len(meshes)):
        return
    for primitive in meshes[mesh_index].get("primitives") or []:
        attributes = primitive.get("attributes") or {}
        position = attributes.get("POSITION")
        if not isinstance(position, int):
            continue
        mode = primitive.get("mode", _TRIANGLES_MODE)
        if mode != _TRIANGLES_MODE:
            notes.append(f"glTF primitive mode {mode} is not triangles and was skipped")
            continue
        base = len(points)
        raw_points = _accessor(document, buffers, position, expect="VEC3")
        points.extend(mat.apply(transform, (row[0], row[1], row[2])) for row in raw_points)
        indices = primitive.get("indices")
        if isinstance(indices, int):
            flat = [int(row[0]) for row in _accessor(document, buffers, indices, expect="SCALAR")]
        else:
            flat = list(range(len(raw_points)))
        for start in range(0, len(flat) - 2, 3):
            faces.extend(triangulate([base + value for value in flat[start:start + 3]]))


def _accessor(document: dict, buffers: list[bytes], index: int, *, expect: str) -> list[tuple[float, ...]]:
    accessors = document.get("accessors") or []
    if not (0 <= index < len(accessors)):
        raise MeshParseError(f"glTF accessor {index} is missing")
    accessor = accessors[index]
    kind = accessor.get("type")
    if kind != expect:
        raise MeshParseError(f"glTF accessor {index} is {kind!r}, expected {expect}")
    component = _COMPONENTS.get(accessor.get("componentType"))
    if component is None:
        raise MeshParseError(f"glTF accessor {index} has an unsupported component type")
    symbol, size = component
    width = _TYPE_COUNTS[kind]
    count = int(accessor.get("count", 0))

    views = document.get("bufferViews") or []
    view_index = accessor.get("bufferView")
    if not isinstance(view_index, int) or not (0 <= view_index < len(views)):
        # A bufferView-less accessor is defined as all zeros.
        return [(0.0,) * width] * count
    view = views[view_index]
    data = buffers[view.get("buffer", 0)] if view.get("buffer", 0) < len(buffers) else b""
    stride = view.get("byteStride") or size * width
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)

    rows: list[tuple[float, ...]] = []
    for row in range(count):
        offset = start + row * stride
        if offset + size * width > len(data):
            raise MeshParseError(f"glTF accessor {index} reads past the end of its buffer")
        rows.append(struct.unpack_from(f"<{width}{symbol}", data, offset))
    return rows
