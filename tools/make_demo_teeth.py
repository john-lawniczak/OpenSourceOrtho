"""Generate smooth, anatomy-shaped demo crown meshes (binary STL).

These are SYNTHETIC educational proxies, not scanned anatomy. They exist so the
Guided demo can exercise the real per-tooth mesh-loading path (``/demo-meshes``
served as static files, parsed by ui/stl.js) and show rounded crowns instead of
the inline primitive proxies.

Each tooth is one closed, deformed UV sphere: a rounded crown on top (+y) with
optional cusps, tapering into a single root below. Built crown-up to match the
viewer's per-arch orientation convention. Re-run after changing proportions:

    python tools/make_demo_teeth.py
"""

from __future__ import annotations

import struct
from math import cos, exp, pi, sin
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "ui" / "demo-meshes"
N_LAT = 18
N_LONG = 24

# Per-class crown/root proportions. cusps are (x, z, height) in crown-normalized
# coordinates; gentle bumps keep the occlusal surface readable without spikes.
PROFILES = {
    "incisor": dict(crown_w=1.1, crown_d=0.5, crown_h=1.45, root_tip=0.12, root_h=1.7,
                    taper_top=0.15, flat_top=0.82, cusps=()),
    "canine": dict(crown_w=0.95, crown_d=0.82, crown_h=1.6, root_tip=0.12, root_h=2.0,
                   taper_top=0.55, flat_top=1.0, cusps=()),
    "premolar": dict(crown_w=1.08, crown_d=1.0, crown_h=1.15, root_tip=0.12, root_h=1.7,
                     taper_top=0.1, flat_top=0.9, cusps=((0.0, -0.4, 0.22), (0.0, 0.4, 0.22))),
    "molar": dict(crown_w=1.48, crown_d=1.32, crown_h=1.05, root_tip=0.12, root_h=1.6,
                  taper_top=0.05, flat_top=0.85, cusps=((-0.42, -0.4, 0.2), (0.42, -0.4, 0.2),
                                                        (-0.42, 0.4, 0.2), (0.42, 0.4, 0.2))),
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _deform(x: float, y: float, z: float, p: dict) -> tuple[float, float, float]:
    if y >= 0:  # crown
        taper = 1.0 - p["taper_top"] * y  # narrow toward the occlusal/incisal edge
        bx, bz, by = x * p["crown_w"] * taper, z * p["crown_d"] * taper, y * p["crown_h"]
        cap = p["crown_h"] * p["flat_top"]
        if by > cap:
            by = cap  # flatten the very tip (incisal edge / occlusal table)
        for cx, cz, ch in p["cusps"]:
            d2 = (x - cx) ** 2 + (z - cz) ** 2
            by += ch * exp(-d2 / 0.12)
        return bx, by, bz
    f = -y  # root: 0 at neck -> 1 at apex
    sx = _lerp(p["crown_w"], p["root_tip"], f)
    sz = _lerp(p["crown_d"], p["root_tip"], f)
    return x * sx, y * p["root_h"], z * sz


def _vertices(p: dict) -> list[list[tuple[float, float, float]]]:
    grid = []
    for i in range(N_LAT + 1):
        theta = pi * i / N_LAT
        ring = []
        for j in range(N_LONG):
            phi = 2 * pi * j / N_LONG
            x, y, z = sin(theta) * cos(phi), cos(theta), sin(theta) * sin(phi)
            ring.append(_deform(x, y, z, p))
        grid.append(ring)
    return grid


def _triangles(grid: list[list[tuple[float, float, float]]]):
    tris = []
    for i in range(N_LAT):
        for j in range(N_LONG):
            jn = (j + 1) % N_LONG
            a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][jn], grid[i][jn]
            tris.append((a, b, c))
            tris.append((a, c, d))
    return tris


def _write_binary_stl(path: Path, tris) -> None:
    with path.open("wb") as fh:
        fh.write(b"OpenSource Ortho synthetic demo crown".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(tris)))
        for v0, v1, v2 in tris:
            fh.write(struct.pack("<3f", 0.0, 0.0, 0.0))  # normal; viewer recomputes
            for v in (v0, v1, v2):
                fh.write(struct.pack("<3f", *v))
            fh.write(struct.pack("<H", 0))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, profile in PROFILES.items():
        tris = _triangles(_vertices(profile))
        _write_binary_stl(OUT_DIR / f"{name}.stl", tris)
        print(f"wrote {name}.stl ({len(tris)} triangles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
