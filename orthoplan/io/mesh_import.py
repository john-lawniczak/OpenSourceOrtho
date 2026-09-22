"""Metadata-only scan inspection across every supported 3D format.

Intake reads the file once and returns both its redacted metadata and its
geometry, so a caller never has to parse the same scan twice. It extracts
geometry metadata only: it never stores mesh bytes, and it never *applies* a
unit. Some formats (3MF, glTF, FBX) declare their unit; that declaration is
reported as ``declared_units`` for the user to confirm, while ``units`` stays
``UNVERIFIED`` until they do.

Point clouds (PLY/OBJ/ASC exports with no faces) are first-class here: they
come back with ``geometry_kind='points'`` and ``face_count=0`` so downstream
code can fail closed on anything that needs a surface.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from orthoplan.io.mesh_formats import (
    SCAN_SUFFIXES,
    SUPPORTED_FORMATS_TEXT,
    MeshParseError,
    MeshPayload,
    Vec3,
    parse_bytes,
)
from orthoplan.model.assets import (
    BoundingBox,
    MeshAsset,
    MeshProvenance,
    MeshQualityReport,
    MeshUnits,
    redact_reference,
)

MAX_SCAN_BYTES = 100 * 1024 * 1024
_DECLARED_UNITS = {
    "millimeter": MeshUnits.MM,
    "centimeter": MeshUnits.CM,
    "meter": MeshUnits.METER,
    "inch": MeshUnits.INCH,
}


@dataclass(frozen=True)
class ScanImport:
    """One inspected scan: redacted metadata plus the geometry behind it."""

    asset: MeshAsset
    payload: MeshPayload

    @property
    def vertices(self) -> list[Vec3]:
        """Triangle-soup vertices for a mesh, or the raw points for a cloud."""

        return self.payload.triangle_soup()


def supported_suffixes() -> tuple[str, ...]:
    return tuple(sorted(SCAN_SUFFIXES))


def is_supported_scan(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SCAN_SUFFIXES


def read_scan(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_SCAN_BYTES,
) -> ScanImport:
    """Inspect a scan file in any supported format, exactly once."""

    resolved = Path(path)
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(f"scan file is too large to inspect safely ({size} bytes)")
    raw = resolved.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    payload = parse_bytes(raw, suffix=resolved.suffix, path=resolved)

    asset = MeshAsset(
        id=sha256[:16],
        format=payload.source_format,
        geometry_kind=payload.kind,
        provenance=provenance,
        units=MeshUnits.UNVERIFIED,
        declared_units=_declared_units(payload),
        vertex_count=len(payload.points),
        face_count=payload.face_count,
        bounds=_bounds(payload.points),
        quality=_quality(payload, resolved),
        sha256=sha256,
        reference=redact_reference(str(resolved)),
    )
    return ScanImport(asset=asset, payload=payload)


def read_mesh_geometry(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_SCAN_BYTES,
) -> tuple[MeshAsset, list[Vec3]]:
    """Metadata plus vertices, for callers that treat geometry as a point set."""

    scan = read_scan(path, provenance=provenance, max_bytes=max_bytes)
    return scan.asset, scan.vertices


def inspect_mesh(
    path: str | Path,
    *,
    provenance: MeshProvenance = MeshProvenance.PATIENT_DERIVED,
    max_bytes: int = MAX_SCAN_BYTES,
) -> MeshAsset:
    """Return redacted, units-unverified metadata for any supported scan file."""

    return read_scan(path, provenance=provenance, max_bytes=max_bytes).asset


def _declared_units(payload: MeshPayload) -> MeshUnits | None:
    return _DECLARED_UNITS.get((payload.declared_units or "").lower())


def _bounds(points: list[Vec3]) -> BoundingBox | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
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


def _quality(payload: MeshPayload, path: Path) -> MeshQualityReport:
    internal = _internal_quality(payload)
    # Watertight/winding are surface properties; a point cloud has neither.
    return _trimesh_quality(path, internal) if payload.faces else internal


def _internal_quality(payload: MeshPayload) -> MeshQualityReport:
    notes = list(payload.notes)
    if not payload.faces:
        return MeshQualityReport(
            inspector=f"internal-{payload.source_format}",
            degenerate_faces=0,
            notes=notes,
        )

    points = payload.points
    degenerate = sum(
        1
        for a, b, c in payload.faces
        if _triangle_area(points[a], points[b], points[c]) == 0
    )
    if degenerate:
        notes.append(f"{degenerate} degenerate triangle(s) detected")
    return MeshQualityReport(
        inspector=f"internal-{payload.source_format}",
        degenerate_faces=degenerate,
        notes=notes,
    )


def _trimesh_quality(path: Path, fallback: MeshQualityReport) -> MeshQualityReport:
    """Add watertight/winding observations when the optional backend is present."""

    if path.suffix.lower() not in SCAN_SUFFIXES:
        return fallback
    try:
        import trimesh
    except ImportError:
        return fallback

    try:
        mesh = trimesh.load_mesh(path, file_type=path.suffix.lower().lstrip("."), process=False)
    except Exception as exc:  # pragma: no cover - depends on optional backend behavior.
        return fallback.model_copy(update={"notes": [*fallback.notes, f"trimesh unavailable: {exc}"]})

    return fallback.model_copy(
        update={
            "inspector": f"{fallback.inspector}+trimesh",
            "watertight": bool(getattr(mesh, "is_watertight", False)),
            "winding_consistent": bool(getattr(mesh, "is_winding_consistent", False)),
        }
    )


__all__ = [
    "MAX_SCAN_BYTES",
    "SUPPORTED_FORMATS_TEXT",
    "MeshParseError",
    "ScanImport",
    "Vec3",
    "inspect_mesh",
    "is_supported_scan",
    "read_mesh_geometry",
    "read_scan",
    "supported_suffixes",
]
