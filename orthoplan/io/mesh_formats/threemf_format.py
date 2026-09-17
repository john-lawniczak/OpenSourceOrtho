"""3MF reader.

3MF is an OPC (ZIP) container whose ``3D/3dmodel.model`` part holds the mesh as
XML. Unlike STL it declares its unit, which is reported as
``declared_units`` - surfaced to the user for confirmation, never applied
silently, because scan scale is a safety-relevant input here.

Objects may be assembled from components and placed by build items, each with
its own affine transform; both are resolved so the geometry lands where the
file says it does.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree

from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    triangulate,
)

_MODEL_PART = "3d/3dmodel.model"
_UNITS = {"micron", "millimeter", "centimeter", "inch", "foot", "meter"}
# 3MF stores an affine placement as 12 numbers: a row-major 4x3 matrix applied
# to a row vector, i.e. p' = [x y z 1] x M.
_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
_MAX_MODEL_BYTES = 400 * 1024 * 1024
_MAX_COMPONENT_DEPTH = 16


def parse(raw: bytes) -> MeshPayload:
    root = ElementTree.fromstring(_model_xml(raw))
    unit = (root.get("unit") or "").strip().lower()
    objects = _objects(root)

    points: list[Vec3] = []
    faces: list[Face] = []
    for object_id, transform in _build_items(root, objects):
        _emit(object_id, transform, objects, points, faces, depth=0)

    notes: list[str] = []
    if unit and unit not in _UNITS:
        notes.append(f"3MF declares an unrecognised unit ({unit!r}); scale must be confirmed")
        unit = ""
    if not faces:
        notes.append("3MF declares no triangles; treated as a point cloud")
    return MeshPayload(
        points=points,
        faces=faces,
        source_format="3mf" if faces else "3mf-points",
        declared_units=unit or None,
        notes=notes,
    )


def _model_xml(raw: bytes) -> bytes:
    try:
        archive = zipfile.ZipFile(BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise MeshParseError("3MF file is not a readable ZIP container") from exc
    with archive:
        match = next(
            (info for info in archive.infolist() if info.filename.lower() == _MODEL_PART),
            None,
        )
        if match is None:
            match = next(
                (info for info in archive.infolist() if info.filename.lower().endswith(".model")),
                None,
            )
        if match is None:
            raise MeshParseError("3MF container has no 3D model part")
        if match.file_size > _MAX_MODEL_BYTES:
            raise MeshParseError(
                f"3MF model part expands to {match.file_size} bytes, above the supported limit"
            )
        try:
            return archive.read(match)
        except (zipfile.BadZipFile, RuntimeError) as exc:
            raise MeshParseError(f"3MF model part could not be read: {exc}") from exc


def _tag(element: ElementTree.Element) -> str:
    return element.tag.rpartition("}")[2].lower()


def _find(parent: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in parent if _tag(child) == name]


def _objects(root: ElementTree.Element) -> dict[str, ElementTree.Element]:
    resources = _find(root, "resources")
    if not resources:
        raise MeshParseError("3MF model declares no resources")
    return {
        obj.get("id", ""): obj
        for resource in resources
        for obj in _find(resource, "object")
        if obj.get("id")
    }


def _build_items(
    root: ElementTree.Element, objects: dict[str, ElementTree.Element]
) -> list[tuple[str, tuple[float, ...]]]:
    items = [
        (item.get("objectid", ""), _transform(item.get("transform")))
        for build in _find(root, "build")
        for item in _find(build, "item")
        if item.get("objectid") in objects
    ]
    # A model with no build section still carries usable geometry; read it as-is.
    return items or [(object_id, _IDENTITY) for object_id in objects]


def _emit(
    object_id: str,
    transform: tuple[float, ...],
    objects: dict[str, ElementTree.Element],
    points: list[Vec3],
    faces: list[Face],
    *,
    depth: int,
) -> None:
    node = objects.get(object_id)
    if node is None or depth > _MAX_COMPONENT_DEPTH:
        return
    for mesh in _find(node, "mesh"):
        _emit_mesh(mesh, transform, points, faces)
    for group in _find(node, "components"):
        for component in _find(group, "component"):
            child = component.get("objectid", "")
            if child and child != object_id:
                _emit(
                    child,
                    _compose(transform, _transform(component.get("transform"))),
                    objects, points, faces, depth=depth + 1,
                )


def _emit_mesh(
    mesh: ElementTree.Element,
    transform: tuple[float, ...],
    points: list[Vec3],
    faces: list[Face],
) -> None:
    base = len(points)
    local: list[Vec3] = []
    for block in _find(mesh, "vertices"):
        for vertex in _find(block, "vertex"):
            local.append(_apply(transform, _vertex(vertex)))
    points.extend(local)
    for block in _find(mesh, "triangles"):
        for triangle in _find(block, "triangle"):
            corners = [triangle.get("v1"), triangle.get("v2"), triangle.get("v3")]
            if any(corner is None for corner in corners):
                raise MeshParseError("3MF triangle is missing a vertex reference")
            indices = [base + int(corner) for corner in corners]  # type: ignore[arg-type]
            if any(index < base or index >= base + len(local) for index in indices):
                raise MeshParseError("3MF triangle references a vertex outside its own mesh")
            faces.extend(triangulate(indices))


def _vertex(element: ElementTree.Element) -> Vec3:
    try:
        return (
            float(element.get("x", "nan")),
            float(element.get("y", "nan")),
            float(element.get("z", "nan")),
        )
    except ValueError as exc:
        raise MeshParseError("3MF vertex has a non-numeric coordinate") from exc


def _transform(raw: str | None) -> tuple[float, ...]:
    if not raw:
        return _IDENTITY
    parts = raw.split()
    if len(parts) != 12:
        raise MeshParseError("3MF transform must have 12 components")
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise MeshParseError("3MF transform has a non-numeric component") from exc


def _apply(matrix: tuple[float, ...], point: Vec3) -> Vec3:
    x, y, z = point
    return (
        x * matrix[0] + y * matrix[3] + z * matrix[6] + matrix[9],
        x * matrix[1] + y * matrix[4] + z * matrix[7] + matrix[10],
        x * matrix[2] + y * matrix[5] + z * matrix[8] + matrix[11],
    )


def _compose(outer: tuple[float, ...], inner: tuple[float, ...]) -> tuple[float, ...]:
    """``inner`` applied first, then ``outer`` (row-vector convention)."""

    values: list[float] = []
    for row in range(4):
        for column in range(3):
            total = sum(inner[row * 3 + step] * outer[step * 3 + column] for step in range(3))
            if row == 3:
                total += outer[9 + column]
            values.append(total)
    return tuple(values)
