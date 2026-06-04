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


def inspect_stl(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_STL_BYTES,
) -> MeshAsset:
    """Return redacted, units-unverified metadata for an STL file."""

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

    return MeshAsset(
        id=sha256[:16],
        format=fmt,
        provenance=provenance,
        units=MeshUnits.UNVERIFIED,
        vertex_count=len(vertices),
        face_count=face_count,
        bounds=_bounds(vertices),
        sha256=sha256,
        reference=redact_reference(str(path)),
    )
