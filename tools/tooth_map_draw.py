"""SVG drawing primitives for the tooth-numbering chart.

Pure presentation helpers used by ``gen_tooth_map.py``. Each tooth is drawn in a
local frame where x = mesiodistal (along the arch) and y = buccolingual, with
+y pointing lingually/inward toward the palate and -y toward the cheek. The
occlusal (biting) surface faces the viewer. Keeping the markup here lets the
generator stay focused on the anatomy data and arch layout.
"""
from __future__ import annotations

# ── Palette ─────────────────────────────────────────────────────────────────
TOOTH_LINE = "#b39d75"
GROOVE = "#bda572"
FOSSA = "#cdb586"
INK = "#13343b"
MUTED = "#62727b"
FDI_INK = "#566a73"
NUM_FILL = "#efedf9"
NUM_LINE = "#bbb2df"
NUM_INK = "#3b3664"


def defs() -> str:
    """Gradients and a soft drop-shadow filter shared by every element."""
    return (
        "<defs>"
        # Domed, top-lit enamel.
        '<radialGradient id="enamel" cx="50%" cy="33%" r="78%">'
        '<stop offset="0%" stop-color="#fffefa"/>'
        '<stop offset="55%" stop-color="#f6f0e1"/>'
        '<stop offset="100%" stop-color="#d8cdaf"/></radialGradient>'
        # Soft white cusp / gloss highlight that fades to nothing.
        '<radialGradient id="cusp" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="#ffffff" stop-opacity="0.9"/>'
        '<stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>'
        "</radialGradient>"
        # Gum: lighter near the teeth, deeper toward the throat.
        '<radialGradient id="gum" cx="50%" cy="30%" r="85%">'
        '<stop offset="0%" stop-color="#f8c2b9"/>'
        '<stop offset="60%" stop-color="#efa39b"/>'
        '<stop offset="100%" stop-color="#df8d86"/></radialGradient>'
        # Palate (upper inner) and tongue (lower inner).
        '<radialGradient id="palate" cx="50%" cy="35%" r="75%">'
        '<stop offset="0%" stop-color="#f3aaa1"/>'
        '<stop offset="100%" stop-color="#d98079"/></radialGradient>'
        '<radialGradient id="tongue" cx="50%" cy="32%" r="80%">'
        '<stop offset="0%" stop-color="#e98e88"/>'
        '<stop offset="100%" stop-color="#c4655f"/></radialGradient>'
        # Mucosa / lip ring behind the gums.
        '<radialGradient id="mucosa" cx="50%" cy="30%" r="90%">'
        '<stop offset="0%" stop-color="#e89991"/>'
        '<stop offset="100%" stop-color="#cf7a73"/></radialGradient>'
        '<filter id="tsh" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="1.3" stdDeviation="1.2" '
        'flood-color="#7a4f47" flood-opacity="0.45"/></filter>'
        '<filter id="psh" x="-25%" y="-25%" width="150%" height="150%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="5" '
        'flood-color="#9c6258" flood-opacity="0.40"/></filter>'
        "</defs>"
    )


def _path(points, closed=True) -> str:
    body = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return body + (" Z" if closed else "")


def mucosa(points) -> str:
    """A darker lip/cheek ring drawn (blurred) behind a gum pad."""
    return f'<path d="{_path(points)}" fill="url(#mucosa)" filter="url(#psh)"/>'


def gum_pad(points) -> str:
    return (f'<path d="{_path(points)}" fill="url(#gum)" stroke="#d2918a" '
            f'stroke-width="1.4" stroke-linejoin="round"/>')


def gingival_collar(points) -> str:
    """A pale, soft band along the tooth line to read as the gum margin."""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (f'<polyline points="{pts}" fill="none" stroke="#fbd3cb" '
            f'stroke-width="13" stroke-linecap="round" stroke-linejoin="round" '
            f'opacity="0.55"/>')


def soft_blob(cx, cy, rx, ry, fill) -> str:
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}"/>'


def palate(cx, cy, rx, ry) -> str:
    """Upper inner surface: a soft dome with a midline raphe and rugae."""
    out = [soft_blob(cx, cy, rx, ry, "url(#palate)")]
    out.append(f'<line x1="{cx}" y1="{cy-ry*0.7:.1f}" x2="{cx}" y2="{cy+ry*0.7:.1f}" '
               f'stroke="#c8746d" stroke-width="1.3" opacity="0.6"/>')
    for i in range(3):
        yy = cy - ry * 0.4 + i * ry * 0.32
        w = rx * (0.55 - i * 0.1)
        out.append(f'<path d="M {cx-w:.1f},{yy:.1f} Q {cx:.1f},{yy-7:.1f} '
                   f'{cx+w:.1f},{yy:.1f}" fill="none" stroke="#cf7d76" '
                   f'stroke-width="1.1" opacity="0.5"/>')
    return "".join(out)


def tongue(cx, cy, rx, ry) -> str:
    """Lower inner surface: a tongue mound with a midline groove and sheen."""
    return (
        soft_blob(cx, cy, rx, ry, "url(#tongue)")
        + f'<line x1="{cx}" y1="{cy-ry*0.72:.1f}" x2="{cx}" y2="{cy+ry*0.55:.1f}" '
          f'stroke="#a8504a" stroke-width="1.6" opacity="0.55"/>'
        + f'<ellipse cx="{cx}" cy="{cy-ry*0.32:.1f}" rx="{rx*0.55:.1f}" '
          f'ry="{ry*0.3:.1f}" fill="#ffffff" opacity="0.16"/>'
    )


# ── Individual crowns (local frame) ─────────────────────────────────────────
def _incisor(hw, hd, w, d) -> str:
    return (
        f'<rect x="{-hw:.1f}" y="{-hd:.1f}" width="{w:.1f}" height="{d:.1f}" '
        f'rx="2" ry="2" fill="url(#enamel)" stroke="{TOOTH_LINE}" stroke-width="1.2"/>'
        f'<rect x="{-hw*0.82:.1f}" y="{-hd*0.82:.1f}" width="{w*0.82:.1f}" '
        f'height="{d*0.5:.1f}" rx="1.5" fill="url(#cusp)"/>'
        f'<line x1="{-hw*0.7:.1f}" y1="{hd*0.55:.1f}" x2="{hw*0.7:.1f}" '
        f'y2="{hd*0.55:.1f}" stroke="{GROOVE}" stroke-width="0.9" opacity="0.6"/>'
    )


def _canine(hw, hd, w, d) -> str:
    tip = -hd - d * 0.18
    pts = (f"{-hw:.1f},{hd*0.85:.1f} {hw:.1f},{hd*0.85:.1f} "
           f"{hw*0.9:.1f},{-hd*0.15:.1f} 0,{tip:.1f} {-hw*0.9:.1f},{-hd*0.15:.1f}")
    return (
        f'<polygon points="{pts}" fill="url(#enamel)" stroke="{TOOTH_LINE}" '
        f'stroke-width="1.2" stroke-linejoin="round"/>'
        f'<polyline points="0,{tip*0.62:.1f} 0,{hd*0.5:.1f}" fill="none" '
        f'stroke="{GROOVE}" stroke-width="1" opacity="0.5"/>'
        f'<ellipse cx="0" cy="{-hd*0.18:.1f}" rx="{hw*0.42:.1f}" '
        f'ry="{hd*0.45:.1f}" fill="url(#cusp)"/>'
    )


def _premolar(hw, hd, w, d) -> str:
    out = [f'<ellipse cx="0" cy="0" rx="{hw:.1f}" ry="{hd:.1f}" fill="url(#enamel)" '
           f'stroke="{TOOTH_LINE}" stroke-width="1.2"/>']
    out.append(f'<line x1="{-hw*0.55:.1f}" y1="0" x2="{hw*0.55:.1f}" y2="0" '
               f'stroke="{GROOVE}" stroke-width="1.1" stroke-linecap="round"/>')
    out.append(f'<ellipse cx="0" cy="{-hd*0.44:.1f}" rx="{hw*0.52:.1f}" '
               f'ry="{hd*0.32:.1f}" fill="url(#cusp)"/>')
    out.append(f'<ellipse cx="0" cy="{hd*0.44:.1f}" rx="{hw*0.46:.1f}" '
               f'ry="{hd*0.3:.1f}" fill="url(#cusp)"/>')
    return "".join(out)


def _molar(hw, hd, w, d) -> str:
    r = min(hw, hd) * 0.42
    out = [f'<rect x="{-hw:.1f}" y="{-hd:.1f}" width="{w:.1f}" height="{d:.1f}" '
           f'rx="{r:.1f}" ry="{r:.1f}" fill="url(#enamel)" stroke="{TOOTH_LINE}" '
           f'stroke-width="1.2"/>']
    # central fossa + cross groove separating four cusps
    out.append(f'<ellipse cx="0" cy="0" rx="{hw*0.5:.1f}" ry="{hd*0.5:.1f}" '
               f'fill="{FOSSA}" opacity="0.45"/>')
    out.append(f'<path d="M 0,{-hd*0.72:.1f} L 0,{hd*0.72:.1f} '
               f'M {-hw*0.72:.1f},0 L {hw*0.72:.1f},0" fill="none" stroke="{GROOVE}" '
               f'stroke-width="1.1" stroke-linecap="round"/>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(f'<ellipse cx="{sx*hw*0.46:.1f}" cy="{sy*hd*0.46:.1f}" '
                       f'rx="{hw*0.33:.1f}" ry="{hd*0.33:.1f}" fill="url(#cusp)"/>')
    return "".join(out)


def tooth_body(kind, w, d) -> str:
    hw, hd = w / 2, d / 2
    if kind == "incisor":
        return _incisor(hw, hd, w, d)
    if kind == "canine":
        return _canine(hw, hd, w, d)
    if kind == "premolar":
        return _premolar(hw, hd, w, d)
    return _molar(hw, hd, w, d)


def number_pill(x, y, text) -> str:
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9.6" fill="{NUM_FILL}" '
            f'stroke="{NUM_LINE}" stroke-width="1"/>'
            f'<ellipse cx="{x:.1f}" cy="{y-3:.1f}" rx="6.5" ry="3" '
            f'fill="#ffffff" opacity="0.5"/>'
            f'<text x="{x:.1f}" y="{y+3.4:.1f}" text-anchor="middle" '
            f'font-size="10.5" font-weight="700" fill="{NUM_INK}">{text}</text>')


def fdi_label(x, y, text) -> str:
    return (f'<text x="{x:.1f}" y="{y+3:.1f}" text-anchor="middle" font-size="9" '
            f'fill="{FDI_INK}" stroke="#ffffff" stroke-width="2.4" '
            f'paint-order="stroke" stroke-linejoin="round">{text}</text>')
