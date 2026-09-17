"""Wavefront OBJ reader.

Only geometry is read: ``v`` vertices and ``f`` faces. Texture coordinates,
normals, materials, groups, and smoothing are skipped - an OBJ exported as a
point cloud simply has no ``f`` lines and comes back as a point cloud.

OBJ face indices are 1-based and may be negative (relative to the end of the
vertex list at the point the face appears), so both are normalised here.
"""

from __future__ import annotations

from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    triangulate,
)


def parse(raw: bytes) -> MeshPayload:
    points: list[Vec3] = []
    faces: list[Face] = []
    skipped_free_form = False

    for line_number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keyword, _, rest = stripped.partition(" ")
        if keyword == "v":
            points.append(_vertex(rest, line_number))
        elif keyword == "f":
            faces.extend(triangulate(_face_indices(rest, len(points), line_number)))
        elif keyword in {"curv", "curv2", "surf"}:
            skipped_free_form = True

    notes: list[str] = []
    if skipped_free_form:
        notes.append("OBJ free-form curve/surface statements were skipped; only polygons are read")
    if not faces:
        notes.append("OBJ declares no faces; treated as a point cloud")
    return MeshPayload(
        points=points,
        faces=faces,
        source_format="obj-points" if not faces else "obj",
        notes=notes,
    )


def _vertex(rest: str, line_number: int) -> Vec3:
    parts = rest.split()
    if len(parts) < 3:
        raise MeshParseError(f"invalid OBJ vertex on line {line_number}")
    try:
        # A 4th component (w) and trailing r/g/b colour are both legal; ignore them.
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError as exc:
        raise MeshParseError(f"invalid OBJ vertex on line {line_number}") from exc


def _face_indices(rest: str, vertex_count: int, line_number: int) -> list[int]:
    indices: list[int] = []
    for token in rest.split():
        # "v", "v/vt", "v//vn", and "v/vt/vn" all start with the vertex index.
        raw_index = token.split("/", 1)[0]
        if not raw_index:
            raise MeshParseError(f"invalid OBJ face on line {line_number}")
        try:
            value = int(raw_index)
        except ValueError as exc:
            raise MeshParseError(f"invalid OBJ face on line {line_number}") from exc
        if value == 0:
            raise MeshParseError(f"OBJ face index 0 is not valid on line {line_number}")
        resolved = value - 1 if value > 0 else vertex_count + value
        if resolved < 0 or resolved >= vertex_count:
            raise MeshParseError(
                f"OBJ face on line {line_number} references vertex {value}, "
                "which is outside the vertices declared before it"
            )
        indices.append(resolved)
    return indices
