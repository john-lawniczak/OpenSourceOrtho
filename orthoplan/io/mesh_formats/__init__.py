"""Scan-file readers, one module per format, behind a single dispatch.

Consumer-grade scanners (Revopoint POP series and friends) export whatever the
user picked in their scanner software, so intake accepts every geometry format
those tools produce and reduces each one to the same :class:`MeshPayload`:

====================  =========================================
Family                Extensions
====================  =========================================
STL                   ``.stl``
PLY                   ``.ply``       mesh or point cloud
Wavefront OBJ         ``.obj``       mesh or point cloud
Plain-text points     ``.asc`` ``.xyz`` ``.pts``
3MF                   ``.3mf``
glTF                  ``.gltf`` ``.glb``
FBX                   ``.fbx``
====================  =========================================

Dispatch is by extension, and falls back to content sniffing when the extension
is unknown or the file is not what it claims to be.
"""

from __future__ import annotations

from pathlib import Path

from orthoplan.io.mesh_formats import (
    fbx_binary,
    fbx_format,
    gltf_format,
    obj_format,
    ply_format,
    points_format,
    stl_format,
    threemf_format,
)
from orthoplan.io.mesh_formats.payload import (
    Face,
    MeshParseError,
    MeshPayload,
    Vec3,
    validated,
)

__all__ = [
    "Face",
    "MeshParseError",
    "MeshPayload",
    "SCAN_SUFFIXES",
    "SUPPORTED_FORMATS_TEXT",
    "Vec3",
    "parse_bytes",
    "parse_file",
    "sniff_family",
]

SCAN_SUFFIXES: dict[str, str] = {
    ".stl": "stl",
    ".ply": "ply",
    ".obj": "obj",
    ".asc": "points",
    ".xyz": "points",
    ".pts": "points",
    ".3mf": "3mf",
    ".gltf": "gltf",
    ".glb": "gltf",
    ".fbx": "fbx",
}

SUPPORTED_FORMATS_TEXT = "STL, PLY, OBJ, ASC/XYZ/PTS, 3MF, glTF/GLB, FBX"

_POINT_SUFFIX_FORMATS = {".asc": "asc-points", ".xyz": "xyz-points", ".pts": "pts-points"}


def parse_file(path: str | Path) -> MeshPayload:
    """Read one scan file into a format-neutral payload."""

    resolved = Path(path)
    return parse_bytes(resolved.read_bytes(), suffix=resolved.suffix, path=resolved)


def parse_bytes(raw: bytes, *, suffix: str = "", path: Path | None = None) -> MeshPayload:
    """Parse scan bytes, using ``suffix`` first and content sniffing as backup."""

    if not raw:
        raise MeshParseError("scan file is empty")
    family = SCAN_SUFFIXES.get(suffix.lower())
    sniffed = sniff_family(raw)
    if family is None:
        if sniffed is None:
            raise MeshParseError(
                f"unsupported scan file {suffix or 'with no extension'!r}; "
                f"supported formats: {SUPPORTED_FORMATS_TEXT}"
            )
        family = sniffed

    try:
        return validated(_dispatch(family, raw, suffix=suffix, path=path))
    except MeshParseError:
        # A renamed or mislabelled export (a PLY saved as .obj, say) should still
        # come in rather than being bounced back to the user over its extension.
        if sniffed is None or sniffed == family:
            raise
        return validated(_dispatch(sniffed, raw, suffix="", path=path))


def _dispatch(family: str, raw: bytes, *, suffix: str, path: Path | None) -> MeshPayload:
    if family == "stl":
        return stl_format.parse(raw)
    if family == "ply":
        return ply_format.parse(raw)
    if family == "obj":
        return obj_format.parse(raw)
    if family == "points":
        return points_format.parse(
            raw, source_format=_POINT_SUFFIX_FORMATS.get(suffix.lower(), "asc-points")
        )
    if family == "3mf":
        return threemf_format.parse(raw)
    if family == "gltf":
        return gltf_format.parse(raw, path=path)
    if family == "fbx":
        return fbx_format.parse(raw)
    raise MeshParseError(f"no reader for scan family {family!r}")


def sniff_family(raw: bytes) -> str | None:
    """Identify a scan family from its content, or ``None`` if unrecognised."""

    if raw[:4] == b"glTF":
        return "gltf"
    if fbx_binary.is_binary_fbx(raw):
        return "fbx"
    if raw[:4] == b"PK\x03\x04":
        return "3mf"
    if raw.lstrip()[:3] == b"ply":
        return "ply"
    if stl_format.looks_binary(raw):
        return "stl"
    return _sniff_text(raw[:64_000])


def _sniff_text(head: bytes) -> str | None:
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError:
        return None
    stripped = text.lstrip()
    if stripped[:5].lower() == "solid" and "facet" in text.lower():
        return "stl"
    if "FBXHeaderExtension" in text:
        return "fbx"
    if stripped[:1] == "{" and '"asset"' in text:
        return "gltf"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if any(line.startswith(("v ", "vn ", "vt ", "f ", "mtllib ", "usemtl ")) for line in lines):
        return "obj"
    if lines and _mostly_numeric(lines):
        return "points"
    return None


def _mostly_numeric(lines: list[str]) -> bool:
    # Ignore the final line: a truncated sniff window usually cuts one in half.
    sample = lines[:-1] if len(lines) > 1 else lines
    parsed = 0
    for line in sample:
        parts = line.replace(",", " ").split()
        if len(parts) >= 3:
            try:
                float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                continue
            parsed += 1
    return bool(sample) and parsed / len(sample) > 0.8
