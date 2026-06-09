"""Bite registration: place an opposing arch pair into one occlusal frame.

The honest core of this module is a distinction:

- **As-scanned** - a real intraoral export (e.g. iTero/OrthoCAD) already registers
  the upper and lower arches into one bite frame using the scanner's buccal-bite
  capture. When we detect that the two arches already occlude (they share an
  occlusal-plane footprint and their biting surfaces sit within an occlusion band),
  we TRUST that registration (identity transform) and only MEASURE it. This is the
  truthful path: the real bite came from the scanner, not from us.
- **Estimated** - when the arches arrive in separate/arbitrary frames (no shared
  footprint, or far apart), we fall back to a plain, clearly-flagged alignment:
  match occlusal-plane centroids and bring the biting surfaces to first contact.
  Two separate arch scans cannot reveal the true bite (that is what a bite scan is
  for), so this mode is ``approximate`` and exists only to make the pair viewable.

The result also carries the registered dentition's millimetre extent, which the 3D
scale reference reads, and the occlusal grid feeds the proximity overlay - the two
features this registration unblocks.

Visualization/review geometry only: never a measured bite, an occlusal-force claim,
or a diagnosis. Gaps are in scan units and are meaningful only once units are
confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orthoplan.model.geometry import Vec3
from orthoplan.occlusion.grid import _CONTACT_BAND, build_occlusal_grid

# Median absolute clearance (scan units) at or below which the arches are treated
# as already occluding, so the scanner's registration is trusted (identity).
_OCCLUSION_BAND = 3.0
# Confidence stays below 1.0: a registration is a draft alignment for review, never
# a measured, clinically-valid bite. Estimated alignments are discounted further.
_MAX_CONFIDENCE = 0.9
_ESTIMATED_DISCOUNT = 0.6


@dataclass(frozen=True)
class BiteRegistration:
    """An opposing arch pair expressed in one occlusal frame, plus quality metrics."""

    mode: str  # "as-scanned" | "estimated" | "unavailable"
    approximate: bool
    # Translation to apply to the LOWER arch to reach the shared frame; (0,0,0) when
    # the arches were already occluding as scanned.
    lower_offset: Vec3
    occlusal_gap_mm: float  # representative vertical clearance at the bite (>= 0)
    interpenetration_mm: float  # deepest surface overlap (>= 0; large = misregistered)
    contact_fraction: float  # share of overlapping cells in occlusal contact
    midline_offset_mm: float  # upper/lower midline (x-centroid) disagreement
    coverage: float  # share of populated cells where the arches overlap in xy
    extent_mm: tuple[float, float, float]  # registered dentition bbox (x, y, z)
    confidence: float
    notes: str


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _centroid_xy(points: list[Vec3], ox: float = 0.0, oy: float = 0.0) -> tuple[float, float]:
    n = len(points)
    return (sum(p[0] for p in points) / n + ox, sum(p[1] for p in points) / n + oy)


def _extent(upper: list[Vec3], lower: list[Vec3], offset: Vec3) -> tuple[float, float, float]:
    ox, oy, oz = offset
    xs = [p[0] for p in upper] + [p[0] + ox for p in lower]
    ys = [p[1] for p in upper] + [p[1] + oy for p in lower]
    zs = [p[2] for p in upper] + [p[2] + oz for p in lower]
    return (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3))


def _estimate_offset(upper: list[Vec3], lower: list[Vec3]) -> Vec3:
    """A plain alignment for non-occluding inputs: centre xy, then first z contact."""

    ucx, ucy = _centroid_xy(upper)
    lcx, lcy = _centroid_xy(lower)
    dx, dy = ucx - lcx, ucy - lcy
    # Bring the lower arch's highest point up to the upper arch's lowest point.
    upper_bottom = min(p[2] for p in upper)
    lower_top = max(p[2] for p in lower)
    dz = upper_bottom - lower_top
    return (dx, dy, dz)


def _confidence(coverage: float, contact: float, approximate: bool) -> float:
    base = min(_MAX_CONFIDENCE, 0.3 + 0.4 * coverage + 0.2 * contact)
    value = base * (_ESTIMATED_DISCOUNT if approximate else 1.0)
    return round(value, 3)


def _unavailable(note: str) -> BiteRegistration:
    return BiteRegistration(
        mode="unavailable",
        approximate=True,
        lower_offset=(0.0, 0.0, 0.0),
        occlusal_gap_mm=0.0,
        interpenetration_mm=0.0,
        contact_fraction=0.0,
        midline_offset_mm=0.0,
        coverage=0.0,
        extent_mm=(0.0, 0.0, 0.0),
        confidence=0.0,
        notes=note,
    )


def register_bite(
    upper: list[Vec3], lower: list[Vec3], *, units_confirmed: bool = True
) -> BiteRegistration:
    """Register an opposing arch pair into one occlusal frame (as-scanned or estimated)."""

    if not upper or not lower:
        return _unavailable("Need both an upper and a lower arch to register a bite.")

    grid = build_occlusal_grid(upper, lower)
    clearances = grid.clearances()
    as_scanned = bool(clearances) and _median([abs(c) for c in clearances]) <= _OCCLUSION_BAND

    if as_scanned:
        offset: Vec3 = (0.0, 0.0, 0.0)
        approximate = False
    else:
        offset = _estimate_offset(upper, lower)
        grid = build_occlusal_grid(upper, lower, lower_offset=offset)
        clearances = grid.clearances()
        approximate = True
        if not clearances:
            return _unavailable("Arches do not share an occlusal footprint even after alignment.")

    contact = sum(1 for c in clearances if abs(c) <= _CONTACT_BAND) / len(clearances)
    ucx, _ = _centroid_xy(upper)
    lcx, _ = _centroid_xy(lower, offset[0])
    notes = (
        "Arches were already occluding as scanned; using the scan's own registration."
        if not approximate
        else "Arches were not pre-registered; this is an APPROXIMATE alignment, not a measured bite."
    )
    if not units_confirmed:
        notes += " Scan units are unconfirmed, so the millimetre values are not yet trustworthy."

    return BiteRegistration(
        mode="as-scanned" if not approximate else "estimated",
        approximate=approximate,
        lower_offset=offset,
        occlusal_gap_mm=round(max(0.0, _median(clearances)), 3),
        interpenetration_mm=round(max(0.0, -min(clearances)), 3),
        contact_fraction=round(contact, 3),
        midline_offset_mm=round(abs(ucx - lcx), 3),
        coverage=round(grid.coverage(), 3),
        extent_mm=_extent(upper, lower, offset),
        confidence=_confidence(grid.coverage(), contact, approximate),
        notes=notes,
    )


def apply_registration(lower: list[Vec3], registration: BiteRegistration) -> list[Vec3]:
    """Return the lower arch vertices moved into the registered shared frame."""

    ox, oy, oz = registration.lower_offset
    return [(p[0] + ox, p[1] + oy, p[2] + oz) for p in lower]


def registration_to_dict(registration: BiteRegistration) -> dict[str, Any]:
    """Serialize a BiteRegistration for an API response (shared by occlusion/segment)."""

    return {
        "mode": registration.mode,
        "approximate": registration.approximate,
        # Translation to apply to the LOWER arch to reach the shared frame; (0,0,0)
        # for as-scanned. The viewer applies it for the registered-bite view.
        "lower_offset": list(registration.lower_offset),
        "occlusal_gap_mm": registration.occlusal_gap_mm,
        "interpenetration_mm": registration.interpenetration_mm,
        "contact_fraction": registration.contact_fraction,
        "midline_offset_mm": registration.midline_offset_mm,
        "coverage": registration.coverage,
        "extent_mm": list(registration.extent_mm),
        "confidence": registration.confidence,
        "notes": registration.notes,
    }
