"""Plain-text point-cloud reader (ASC, XYZ, PTS).

Revo Scan exports point-cloud models as ASC; XYZ and PTS are the same idea from
other scanners. There is no header standard, so the reader is deliberately
forgiving: it takes the first three numeric columns of every parsable line and
ignores anything else on it (normals, RGB, intensity) plus comment and header
lines.

A point cloud has no surface. Downstream code must check ``kind`` before doing
anything triangle-based with it.
"""

from __future__ import annotations

from orthoplan.io.mesh_formats.payload import MeshParseError, MeshPayload, Vec3

# A leading count line (PTS) or a stray header word should not fail the whole
# file, but a file that is mostly unparsable is not a point cloud at all.
_MAX_UNPARSED_RATIO = 0.25


def parse(raw: bytes, *, source_format: str = "asc-points") -> MeshPayload:
    points: list[Vec3] = []
    considered = 0
    skipped = 0

    for line in raw.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", ";")):
            continue
        considered += 1
        point = _point(stripped)
        if point is None:
            skipped += 1
        else:
            points.append(point)

    if not points:
        raise MeshParseError("point-cloud file contains no readable XYZ rows")
    if considered and skipped / considered > _MAX_UNPARSED_RATIO:
        raise MeshParseError(
            f"{skipped} of {considered} rows are not XYZ triples; "
            "this does not look like a point-cloud export"
        )

    notes = ["point cloud: no faces, so surface-based checks are unavailable"]
    if skipped:
        notes.append(f"{skipped} non-numeric row(s) skipped (header or comment lines)")
    return MeshPayload(points=points, faces=[], source_format=source_format, notes=notes)


def _point(line: str) -> Vec3 | None:
    parts = line.replace(",", " ").replace("\t", " ").split()
    if len(parts) < 3:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        return None
