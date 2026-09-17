"""Canonical on-disk form for a registered scan.

Scans arrive in any of the supported formats but are stored one way, so that
every downstream consumer - the viewer, segmentation, the print package - reads
a single shape instead of re-implementing seven parsers:

- a mesh becomes a binary STL (``.stl``)
- a point cloud becomes a plain-text XYZ file (``.xyz``), because STL has no
  way to represent points without faces

The original file's bytes are hashed into the asset id before conversion, so
provenance still tracks what the user actually uploaded.
"""

from __future__ import annotations

import struct

from orthoplan.io.mesh_formats.payload import MeshPayload, Vec3

Triangle = tuple[Vec3, Vec3, Vec3]

CANONICAL_STL_HEADER = b"OpenSource Ortho canonical scan (metadata only; review required)"
_SEGMENT_HEADER = b"OpenSource Ortho auto-segment (model-generated, review required)"


def canonical_suffix(payload: MeshPayload) -> str:
    return ".stl" if payload.faces else ".xyz"


def canonical_bytes(payload: MeshPayload) -> bytes:
    """Serialize a parsed scan into its canonical storage form."""

    if payload.faces:
        return binary_stl_bytes(payload.triangles(), header=CANONICAL_STL_HEADER)
    return xyz_points_bytes(payload.points)


def binary_stl_bytes(triangles: list[Triangle], *, header: bytes = _SEGMENT_HEADER) -> bytes:
    """Serialize triangles to a standard 80-byte-header binary STL."""

    out = bytearray()
    out += header[:80].ljust(80, b" ")
    out += struct.pack("<I", len(triangles))
    for tri in triangles:
        nx, ny, nz = facet_normal(tri)
        out += struct.pack("<12fH", nx, ny, nz, *tri[0], *tri[1], *tri[2], 0)
    return bytes(out)


def xyz_points_bytes(points: list[Vec3]) -> bytes:
    """One ``x y z`` row per point, the plainest form every XYZ reader accepts."""

    rows = [f"{x:.6f} {y:.6f} {z:.6f}" for x, y, z in points]
    return ("\n".join(rows) + "\n").encode("ascii")


def facet_normal(tri: Triangle) -> Vec3:
    """Unit normal from triangle winding; ``(0, 0, 0)`` when degenerate."""

    ax, ay, az = (tri[1][index] - tri[0][index] for index in range(3))
    bx, by, bz = (tri[2][index] - tri[0][index] for index in range(3))
    nx, ny, nz = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)
