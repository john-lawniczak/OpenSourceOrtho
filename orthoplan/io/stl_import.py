"""Metadata-only STL inspection.

Phase 1 uses a small internal reader (no third-party mesh dependency yet). It
extracts only geometry metadata; it never stores mesh bytes and never infers
units (STL has none), so units are reported as ``UNVERIFIED``.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from orthoplan.model.assets import (
    BoundingBox,
    MeshAsset,
    MeshProvenance,
    MeshQualityReport,
    MeshUnits,
    redact_reference,
)

Vec3 = tuple[float, float, float]
MAX_STL_BYTES = 100 * 1024 * 1024


def _looks_binary(raw: bytes) -> bool:
    if len(raw) < 84:
        return False
    (count,) = struct.unpack_from("<I", raw, 80)
    return len(raw) == 84 + count * 50


def _read_binary(raw: bytes) -> tuple[int, list[Vec3]]:
    (count,) = struct.unpack_from("<I", raw, 80)
    vertices: list[Vec3] = []
    offset = 84
    for _ in range(count):
        # 12 floats per facet: normal(3) + v0(3) + v1(3) + v2(3); skip normal.
        values = struct.unpack_from("<12f", raw, offset)
        vertices.extend((values[3:6], values[6:9], values[9:12]))
        offset += 50
    return count, vertices


def _read_ascii(raw: bytes) -> tuple[int, list[Vec3]]:
    text = raw.decode("utf-8", errors="replace")
    vertices: list[Vec3] = []
    facets = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("facet normal"):
            facets += 1
        elif stripped.startswith("vertex"):
            parts = stripped.split()
            if len(parts) >= 4:
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError as exc:
                    raise ValueError(f"invalid STL vertex on line {line_number}") from exc
    return facets, vertices


def _bounds(vertices: list[Vec3]) -> BoundingBox | None:
    if not vertices:
        return None
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return BoundingBox(
        min_xyz=(min(xs), min(ys), min(zs)),
        max_xyz=(max(xs), max(ys), max(zs)),
    )


def _triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5


def _internal_quality(face_count: int, vertices: list[Vec3]) -> MeshQualityReport:
    degenerate = 0
    for index in range(0, len(vertices), 3):
        if index + 2 < len(vertices) and _triangle_area(*vertices[index : index + 3]) == 0:
            degenerate += 1

    notes: list[str] = []
    if degenerate:
        notes.append(f"{degenerate} degenerate triangle(s) detected")
    if len(vertices) != face_count * 3:
        notes.append("facet and vertex counts differ from the expected STL triangle layout")

    return MeshQualityReport(
        inspector="internal-stl",
        degenerate_faces=degenerate,
        notes=notes,
    )


def _trimesh_quality(path: Path, fallback: MeshQualityReport) -> MeshQualityReport:
    try:
        import trimesh
    except ImportError:
        return fallback

    try:
        mesh = trimesh.load_mesh(path, file_type="stl", process=False)
    except Exception as exc:  # pragma: no cover - depends on optional backend behavior.
        return fallback.model_copy(update={"notes": [*fallback.notes, f"trimesh unavailable: {exc}"]})

    return fallback.model_copy(
        update={
            "inspector": "internal-stl+trimesh",
            "watertight": bool(getattr(mesh, "is_watertight", False)),
            "winding_consistent": bool(getattr(mesh, "is_winding_consistent", False)),
        }
    )


def read_stl_geometry(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_STL_BYTES,
) -> tuple[MeshAsset, list[Vec3]]:
    """Inspect an STL once and return both its metadata and its vertices.

    Vertices are returned for callers that need geometry (e.g. per-tooth frame
    estimation) so the file is read a single time.
    """

    path = Path(path)
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"STL file is too large to inspect safely ({size} bytes)")
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()

    if _looks_binary(raw):
        fmt, (face_count, vertices) = "stl-binary", _read_binary(raw)
    else:
        fmt, (face_count, vertices) = "stl-ascii", _read_ascii(raw)

    if face_count <= 0 or not vertices:
        raise ValueError("STL contains no readable facets or vertices")
    if len(vertices) < face_count * 3:
        raise ValueError("STL facet and vertex counts are inconsistent")

    quality = _trimesh_quality(path, _internal_quality(face_count, vertices))
    asset = MeshAsset(
        id=sha256[:16],
        format=fmt,
        provenance=provenance,
        units=MeshUnits.UNVERIFIED,
        vertex_count=len(vertices),
        face_count=face_count,
        bounds=_bounds(vertices),
        quality=quality,
        sha256=sha256,
        reference=redact_reference(str(path)),
    )
    return asset, vertices


def inspect_stl(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_STL_BYTES,
) -> MeshAsset:
    """Return redacted, units-unverified metadata for an STL file."""

    asset, _ = read_stl_geometry(path, provenance=provenance, max_bytes=max_bytes)
    return asset
