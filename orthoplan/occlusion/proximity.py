"""Occlusal proximity map: classify per-cell clearance into review colour bands.

Consumes the occlusal grid (the registered opposing arches' per-cell biting-surface
heights) and labels each shared cell by how close the two surfaces are:

- ``contact``   surfaces touching or overlapping (signed clearance <= contact band)
- ``near``      close but not touching (within the near band)
- ``clearance`` an open gap between the arches

The 3D viewer paints these red / amber / green - the "where do the arches meet"
overlay, like an intraoral scanner's occlusion view.

CRITICAL FRAMING: this is a GEOMETRIC proximity map (how close the registered crown
surfaces are), NOT a measurement of bite force or contact pressure, and NOT an
occlusal analysis. Closeness is not force: a cell is red because the surfaces are
near/overlapping in the registered geometry, which says nothing about load, timing,
or whether the bite is healthy. It never diagnoses or asserts a bite is correct or
complete. Clearance values are in scan units and mean nothing until units are
confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orthoplan.occlusion.grid import _CONTACT_BAND, OcclusalGrid
from orthoplan.occlusion.registration import BiteRegistration

# Clearance (scan units) at/below which a cell is "contact"; up to here "near";
# beyond, "clearance". Geometric review bands, not force - deliberately coarse.
_CONTACT_THRESHOLD = _CONTACT_BAND  # 0.5
_NEAR_THRESHOLD = 1.5

PROXIMITY_CAVEAT = (
    "This is a geometric proximity map: it colours how close the registered crown "
    "surfaces are (red = touching/overlapping, amber = near, green = clearance). It "
    "is NOT bite force or contact pressure, NOT an occlusal analysis, and NOT a "
    "diagnosis. Review it; closeness in the scan geometry does not mean load or that "
    "the bite is correct."
)


@dataclass(frozen=True)
class ProximityCell:
    """One occlusal-grid cell, located in scan space, with its clearance band."""

    cx: float  # scan-space cell centre (mediolateral)
    cy: float  # scan-space cell centre (anteroposterior)
    cz: float  # scan-space height of the meeting plane (midway between surfaces)
    clearance: float  # signed: + gap, ~0 contact, - interpenetration
    band: str  # "contact" | "near" | "clearance"


@dataclass(frozen=True)
class ProximityMap:
    """A classified occlusal proximity overlay for an opposing arch pair."""

    cell_size: float
    cells: list[ProximityCell]
    contact_threshold: float
    near_threshold: float
    counts: dict[str, int]
    # The overlay's scan-space coordinates only match the rendered scan geometry
    # when the registration was the scan's own (as-scanned). For an estimated
    # alignment the lower arch was shifted, so the viewer must NOT paint it onto the
    # unshifted scans - it would mislead. This flag gates that.
    aligned_to_scan: bool
    approximate: bool
    units_confirmed: bool
    caveat: str = PROXIMITY_CAVEAT


def _band(clearance: float) -> str:
    if clearance <= _CONTACT_THRESHOLD:
        return "contact"
    if clearance <= _NEAR_THRESHOLD:
        return "near"
    return "clearance"


def classify_proximity(
    grid: OcclusalGrid, registration: BiteRegistration, *, units_confirmed: bool = True
) -> ProximityMap:
    """Label each shared occlusal cell by clearance band, located in scan space."""

    cells: list[ProximityCell] = []
    counts = {"contact": 0, "near": 0, "clearance": 0}
    for key in grid.shared_cells():
        ix, iy = key
        upper_bottom = grid.upper_bottom[key]
        lower_top = grid.lower_top[key]
        clearance = upper_bottom - lower_top
        band = _band(clearance)
        counts[band] += 1
        cells.append(
            ProximityCell(
                cx=round(grid.lo_x + (ix + 0.5) * grid.cell_size, 3),
                cy=round(grid.lo_y + (iy + 0.5) * grid.cell_size, 3),
                cz=round((upper_bottom + lower_top) / 2.0, 3),
                clearance=round(clearance, 3),
                band=band,
            )
        )
    return ProximityMap(
        cell_size=round(grid.cell_size, 4),
        cells=cells,
        contact_threshold=_CONTACT_THRESHOLD,
        near_threshold=_NEAR_THRESHOLD,
        counts=counts,
        aligned_to_scan=not registration.approximate,
        approximate=registration.approximate,
        units_confirmed=units_confirmed,
    )


def proximity_map_to_dict(pmap: ProximityMap) -> dict[str, Any]:
    """Serialize a ProximityMap for the /api/occlusion response and the viewer."""

    return {
        "cell_size": pmap.cell_size,
        "contact_threshold": pmap.contact_threshold,
        "near_threshold": pmap.near_threshold,
        "counts": pmap.counts,
        "aligned_to_scan": pmap.aligned_to_scan,
        "approximate": pmap.approximate,
        "units_confirmed": pmap.units_confirmed,
        "caveat": pmap.caveat,
        "cells": [
            {"x": c.cx, "y": c.cy, "z": c.cz, "clearance": c.clearance, "band": c.band}
            for c in pmap.cells
        ],
    }
