"""Write per-tooth segment triangles to binary STL and register them locally.

Each :class:`~orthoplan.segmentation.heuristic.ToothSegment` becomes a binary STL
under the local mesh workspace (provenance ``model-generated``), so it is served
by ``GET /api/mesh/<id>`` exactly like any other registered tooth mesh. Nothing
leaves the machine; this is the on-device path.
"""

from __future__ import annotations

import os
import struct
import tempfile

from orthoplan.model.assets import MeshAsset, MeshProvenance
from orthoplan.mesh_workspace import register_stl_mesh
from orthoplan.segmentation.heuristic import Triangle, ToothSegment

_STL_HEADER = b"OpenSource Ortho auto-segment (model-generated, review required)"


def _normal(tri: Triangle) -> tuple[float, float, float]:
    ax, ay, az = (tri[1][i] - tri[0][i] for i in range(3))
    bx, by, bz = (tri[2][i] - tri[0][i] for i in range(3))
    nx, ny, nz = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def binary_stl_bytes(triangles: list[Triangle]) -> bytes:
    """Serialize triangles to a standard 80-byte-header binary STL."""

    out = bytearray()
    out += _STL_HEADER[:80].ljust(80, b" ")
    out += struct.pack("<I", len(triangles))
    for tri in triangles:
        nx, ny, nz = _normal(tri)
        out += struct.pack(
            "<12fH",
            nx, ny, nz,
            *tri[0], *tri[1], *tri[2],
            0,
        )
    return bytes(out)


def write_segment_meshes(
    segments: list[ToothSegment],
    *,
    workspace: str | os.PathLike[str] | None = None,
) -> list[tuple[ToothSegment, MeshAsset]]:
    """Write + register one binary STL per segment; return (segment, asset) pairs."""

    results: list[tuple[ToothSegment, MeshAsset]] = []
    for segment in segments:
        data = binary_stl_bytes(segment.triangles)
        tmp = tempfile.NamedTemporaryFile(suffix=".stl", delete=False)
        try:
            tmp.write(data)
            tmp.close()
            asset = register_stl_mesh(
                tmp.name,
                workspace=workspace,
                provenance=MeshProvenance.MODEL_GENERATED,
            )
        finally:
            os.unlink(tmp.name)
        results.append((segment, asset))
    return results
