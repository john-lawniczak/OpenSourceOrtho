"""Occlusal grid: the shared substrate for bite registration and proximity mapping.

Buckets two opposing whole-arch crown surfaces into a common occlusal-plane (xy)
grid and records, per cell, the BITING-surface height of each arch: the upper
arch's lowest ``z`` (its surface faces down toward the bite) and the lower arch's
highest ``z`` (faces up), because ``+z`` is occlusal-superior in the shared scan
frame (see ``model.geometry``). The per-cell signed clearance
(``upper_bottom - lower_top``) is the single signal both the registration metrics
and the future red/yellow/green proximity overlay read:

- ``> 0``  vertical clearance (a gap between the arches in that cell)
- ``~ 0``  occlusal contact
- ``< 0``  the surfaces overlap / interpenetrate

Pure list math, dependency-free, deterministic, O(n) over the input vertices.

This is geometry for visualization and review only. It is NOT a measured bite, an
occlusal-force map, or a diagnosis, and it never asserts that a bite is correct,
healthy, or complete.
"""

from __future__ import annotations

from dataclasses import dataclass

from orthoplan.model.geometry import Vec3

# Grid resolution: this many cells across the wider occlusal-plane span. ~48 cells
# over a ~60 mm arch is a ~1.3 mm cell - fine enough for contact structure, coarse
# enough to stay O(cells) on the metrics while bucketing is O(vertices).
_DEFAULT_TARGET_CELLS = 48
# Cells whose two biting surfaces are within this many scan units count as occlusal
# CONTACT, as opposed to a clearance gap or an interpenetration.
_CONTACT_BAND = 0.5


@dataclass(frozen=True)
class OcclusalGrid:
    """Per-cell biting-surface heights of an opposing arch pair in a shared frame."""

    cell_size: float
    lo_x: float
    lo_y: float
    nx: int
    ny: int
    # Keyed by (ix, iy): the upper arch's lowest z and the lower arch's highest z in
    # that occlusal-plane cell (the two surfaces that face each other in the bite).
    upper_bottom: dict[tuple[int, int], float]
    lower_top: dict[tuple[int, int], float]

    def shared_cells(self) -> list[tuple[int, int]]:
        """Cells where BOTH arches have surface - the only cells with a clearance."""

        return [key for key in self.upper_bottom if key in self.lower_top]

    def clearances(self) -> list[float]:
        """Signed gap per shared cell: + clearance, ~0 contact, - interpenetration."""

        return [self.upper_bottom[key] - self.lower_top[key] for key in self.shared_cells()]

    def coverage(self) -> float:
        """Fraction of populated cells where the two arches actually overlap in xy."""

        union = set(self.upper_bottom) | set(self.lower_top)
        return len(self.shared_cells()) / len(union) if union else 0.0


def _xy_bounds(
    points: list[Vec3], ox: float, oy: float
) -> tuple[float, float, float, float]:
    xs_min = min(p[0] + ox for p in points)
    xs_max = max(p[0] + ox for p in points)
    ys_min = min(p[1] + oy for p in points)
    ys_max = max(p[1] + oy for p in points)
    return xs_min, xs_max, ys_min, ys_max


def _bucket(value: float, lo: float, cell: float, n: int) -> int:
    if cell <= 0:
        return 0
    return min(n - 1, max(0, int((value - lo) / cell)))


def build_occlusal_grid(
    upper: list[Vec3],
    lower: list[Vec3],
    *,
    lower_offset: Vec3 = (0.0, 0.0, 0.0),
    target_cells: int = _DEFAULT_TARGET_CELLS,
) -> OcclusalGrid:
    """Bucket two arches into a shared occlusal grid (lower shifted by ``lower_offset``).

    ``lower_offset`` lets the registration rebuild the grid for an estimated shift
    without materialising a transformed copy of a million-vertex arch.
    """

    ox, oy, oz = lower_offset
    u_minx, u_maxx, u_miny, u_maxy = _xy_bounds(upper, 0.0, 0.0)
    l_minx, l_maxx, l_miny, l_maxy = _xy_bounds(lower, ox, oy)
    lo_x, hi_x = min(u_minx, l_minx), max(u_maxx, l_maxx)
    lo_y, hi_y = min(u_miny, l_miny), max(u_maxy, l_maxy)
    span = max(hi_x - lo_x, hi_y - lo_y)
    cell = span / target_cells if span > 0 else 1.0
    nx = max(1, int((hi_x - lo_x) / cell) + 1)
    ny = max(1, int((hi_y - lo_y) / cell) + 1)

    upper_bottom: dict[tuple[int, int], float] = {}
    for px, py, pz in upper:
        key = (_bucket(px, lo_x, cell, nx), _bucket(py, lo_y, cell, ny))
        prev = upper_bottom.get(key)
        if prev is None or pz < prev:
            upper_bottom[key] = pz
    lower_top: dict[tuple[int, int], float] = {}
    for px, py, pz in lower:
        key = (_bucket(px + ox, lo_x, cell, nx), _bucket(py + oy, lo_y, cell, ny))
        z = pz + oz
        prev = lower_top.get(key)
        if prev is None or z > prev:
            lower_top[key] = z

    return OcclusalGrid(cell, lo_x, lo_y, nx, ny, upper_bottom, lower_top)
