"""Back-compatible STL entry points.

Intake is format-neutral now and lives in :mod:`orthoplan.io.mesh_import`; STL
is one reader among several. These names stay so existing callers (and any
downstream scripts) keep working, and they accept every supported scan format
rather than STL alone.

New code should import from :mod:`orthoplan.io.mesh_import` directly.
"""

from __future__ import annotations

from orthoplan.io.mesh_import import (
    MAX_SCAN_BYTES,
    Vec3,
    inspect_mesh,
    read_mesh_geometry,
    read_scan,
)

#: Deprecated alias kept for callers that still say "STL".
MAX_STL_BYTES = MAX_SCAN_BYTES

inspect_stl = inspect_mesh
read_stl_geometry = read_mesh_geometry

__all__ = [
    "MAX_SCAN_BYTES",
    "MAX_STL_BYTES",
    "Vec3",
    "inspect_mesh",
    "inspect_stl",
    "read_mesh_geometry",
    "read_scan",
    "read_stl_geometry",
]
