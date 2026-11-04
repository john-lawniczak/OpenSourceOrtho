#!/usr/bin/env python3
"""Generate the tooth-numbering chart SVG (Universal + FDI).

An educational diagram, not a clinical record. It is an occlusal ("looking into
the mouth") view: upper and lower gum pads with a palate / tongue, framed by
mucosa, with the teeth drawn as their biting-surface silhouettes. Crown sizes
follow standard mean dimensions (the upper central incisor is wide; the lower
central incisor is the smallest tooth; the first molars are the largest) and
each family has its own shape (thin incisors, pointed canines, two-cusp
premolars, four-cusp molars).

Each tooth shows its Universal number (large, in a circle, US 1-32) and its FDI
number (small, on the cheek side -- the system the app uses internally). The
numbers are a layout convention: the patient's right side is on the viewer's left.

Run:  python3 tools/gen_tooth_map.py
It writes identical SVGs to ui/tooth-chart.svg and docs/images/fdi-tooth-map.svg.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import tooth_map_draw as draw

# ── Canvas ────────────────────────────────────────────────────────────────
W, H = 640, 760
CX = 320.0
UP_CY, UP_RX, UP_RY = 340.0, 155.0, 240.0     # upper arch (opens downward)
LO_CY, LO_RX, LO_RY = 420.0, 155.0, 240.0     # lower arch (mirror)
W_SCALE, D_SCALE = 3.9, 3.0                   # mm -> px crown scaling
GUM_OUT = 18                                   # gum pad reach past the teeth (px)
GUM_INNER_F = 0.24                             # inner gum radius / arch radius

# ── Tooth specification ─────────────────────────────────────────────────────
# Position from the midline -> crown dimensions in mm (Wheeler / Ash means).
MAX_W = {1: 8.5, 2: 6.5, 3: 7.5, 4: 7.0, 5: 6.5, 6: 10.0, 7: 9.0, 8: 8.5}
MAX_D = {1: 4.6, 2: 4.4, 3: 6.4, 4: 7.6, 5: 7.6, 6: 8.6, 7: 8.6, 8: 8.2}
MAND_W = {1: 5.0, 2: 5.5, 3: 7.0, 4: 7.0, 5: 7.0, 6: 11.0, 7: 10.5, 8: 9.5}
MAND_D = {1: 4.0, 2: 4.2, 3: 6.0, 4: 6.8, 5: 6.8, 6: 9.2, 7: 9.0, 8: 8.6}
KIND = {1: "incisor", 2: "incisor", 3: "canine", 4: "premolar",
        5: "premolar", 6: "molar", 7: "molar", 8: "molar"}

# Left half runs back->front (positions 8..1), right half front->back (1..8).
POSITIONS = [8, 7, 6, 5, 4, 3, 2, 1, 1, 2, 3, 4, 5, 6, 7, 8]
UNIVERSAL_UPPER = list(range(1, 17))
UNIVERSAL_LOWER = list(range(32, 16, -1))
FDI_UPPER = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
FDI_LOWER = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]


@dataclass
class Arch:
    cy: float
    rx: float
    ry: float
    lower: bool


UPPER = Arch(UP_CY, UP_RX, UP_RY, False)
LOWER = Arch(LO_CY, LO_RX, LO_RY, True)


@dataclass
class Tooth:
    cx: float
    cy: float
    rot: float
    w: float
    d: float
    kind: str
    universal: int
    fdi: int


def arch_point(f, a: Arch, dr=0.0):
    """Point on an arch curve; f in [0,1] runs left -> right. dr scales radius."""
    # A parabolic U: posterior rows straighten instead of closing into an oval.
    u = 2 * f - 1
    x = (a.rx + dr) * math.sin(u * math.pi / 2)
    depth = (a.ry + dr) * (1 - abs(u) ** 1.7)
    return CX + x, a.cy + (depth if a.lower else -depth)


def layout(a: Arch, widths_mm, depths_mm, universal, fdi):
    widths_px = [widths_mm[p] * W_SCALE for p in POSITIONS]
    total = sum(widths_px)
    samples = [arch_point(i / 1000, a) for i in range(1001)]
    lengths = [0.0]
    for first, second in zip(samples, samples[1:]):
        lengths.append(lengths[-1] + math.dist(first, second))
    teeth, run = [], 0.0
    for i, pos in enumerate(POSITIONS):
        f = (run + widths_px[i] / 2) / total
        run += widths_px[i]
        target = f * lengths[-1]
        f = next(j for j, length in enumerate(lengths) if length >= target) / 1000
        px, py = arch_point(f, a)
        before, after = arch_point(max(0, f - .001), a), arch_point(min(1, f + .001), a)
        rot = math.degrees(math.atan2(after[1] - before[1], after[0] - before[0]))
        if a.lower:
            rot += 180
        teeth.append(Tooth(px, py, rot, widths_px[i], depths_mm[pos] * D_SCALE,
                           KIND[pos], universal[i], fdi[i]))
    return teeth


def _gum_points(a: Arch):
    pts = [arch_point(k / 40, a, GUM_OUT) for k in range(41)]
    inner = -20
    pts += [arch_point(1 - k / 40, a, inner) for k in range(41)]
    return pts


def _scene(a: Arch, cavity):
    """Mucosa frame, gum pad, gingival collar and the inner soft-tissue."""
    gp = _gum_points(a)
    mucosa = [arch_point(k / 40, a, GUM_OUT + 9) for k in range(41)]
    mucosa += [arch_point(1 - k / 40, a, -25) for k in range(41)]
    collar = [arch_point(k / 60, a) for k in range(61)]
    return draw.mucosa(mucosa) + draw.gum_pad(gp) + draw.gingival_collar(collar)


def _tooth_svg(t: Tooth) -> str:
    group = (f'<g transform="translate({t.cx:.1f},{t.cy:.1f}) rotate({t.rot:.1f})" '
             f'filter="url(#tsh)">{draw.tooth_body(t.kind, t.w, t.d)}</g>')
    ang = math.radians(t.rot)
    inx, iny = -math.sin(ang), math.cos(ang)
    nx, ny = t.cx + inx * (t.d / 2 + 13), t.cy + iny * (t.d / 2 + 13)
    fx, fy = t.cx - inx * (t.d / 2 + 12), t.cy - iny * (t.d / 2 + 12)
    return group + draw.number_pill(nx, ny, t.universal) + draw.fdi_label(fx, fy, t.fdi)


def _labels() -> str:
    out = []
    for lx, ly, big, small in [(CX, 240, "UPPER ARCH", "(maxillary)"),
                               (CX, 530, "LOWER ARCH", "(mandibular)")]:
        out.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="12" '
                   f'fill="#496965" opacity="0.92" letter-spacing="1">{big}</text>')
        out.append(f'<text x="{lx}" y="{ly+14}" text-anchor="middle" font-size="9.5" '
                   f'fill="#496965" opacity="0.8">{small}</text>')
    for cxq, cyq, txt in [(80, 230, "Upper right"), (560, 230, "Upper left"),
                          (80, 530, "Lower right"), (560, 530, "Lower left")]:
        out.append(f'<text x="{cxq}" y="{cyq}" text-anchor="middle" font-size="10.5" '
                   f'font-weight="600" fill="{draw.MUTED}">{txt}</text>')
    return "".join(out)


def _legend() -> str:
    return (
        f'<text x="{CX}" y="720" text-anchor="middle" font-size="11" '
        f'fill="{draw.INK}"><tspan font-weight="700">Circled number</tspan> = '
        f'Universal (US 1&#8211;32) &#183; <tspan font-weight="700">small number'
        f'</tspan> = FDI (used by this app)</text>'
        f'<text x="{CX}" y="740" text-anchor="middle" font-size="10" '
        f'fill="{draw.MUTED}">Their right side is on your left. '
        f'FDI = quadrant digit (1 UR &#183; 2 UL &#183; 3 LL &#183; 4 LR) + tooth '
        f'from midline (1 front &#8594; 8 back).</text>'
    )


def build_svg() -> str:
    upper = layout(UPPER, MAX_W, MAX_D, UNIVERSAL_UPPER, FDI_UPPER)
    lower = layout(LOWER, MAND_W, MAND_D, UNIVERSAL_LOWER, FDI_LOWER)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="system-ui,Segoe UI,Roboto,sans-serif" role="img" '
        f'aria-label="Mouth diagram with Universal (1-32) and FDI tooth numbers">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        draw.defs(),
        f'<text x="{CX}" y="26" text-anchor="middle" font-size="17" '
        f'font-weight="700" fill="#0f3d3a">Tooth numbering &#8212; Universal '
        f'(1&#8211;32) &amp; FDI</text>',
        _scene(UPPER, "palate"),
        _scene(LOWER, "tongue"),
        _labels(),
    ]
    out += [_tooth_svg(t) for t in upper + lower]
    out += [_legend(), "</svg>"]
    return "\n".join(out) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    svg = build_svg()
    for rel in ("ui/tooth-chart.svg", "docs/images/fdi-tooth-map.svg"):
        (root / rel).write_text(svg, encoding="utf-8")
        print(f"wrote {rel} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
