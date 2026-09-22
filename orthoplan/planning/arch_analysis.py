"""Deterministic arch-form and space analysis from per-tooth crown landmarks.

Given the occlusal-plane centroids of one arch's teeth, this computes:

- per-tooth corrective movement onto a fitted arch curve (the real crowding
  signal, via ``arch_form.archform_corrections``),
- an arch-length discrepancy (space required vs available), and
- an interproximal-reduction (IPR) budget to recover crowding space.

Honesty: "space required" uses a typical mesiodistal crown-width table, which is
a population heuristic, not a measurement of this patient's crowns (real crown
widths need segmentation). That limitation is reported as a data gap. Nothing
here infers roots/bone or claims a plan is safe.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from math import hypot

from orthoplan.planning.arch_form import archform_corrections

# Typical average mesiodistal crown widths (mm) by FDI position digit. Population
# heuristic for space analysis only - see module docstring / data_gap below.
_WIDTHS_MAXILLARY = {"1": 8.5, "2": 6.5, "3": 7.6, "4": 7.0, "5": 6.6, "6": 10.0, "7": 9.5, "8": 8.5}
_WIDTHS_MANDIBULAR = {"1": 5.3, "2": 5.7, "3": 6.7, "4": 7.0, "5": 7.1, "6": 11.0, "7": 10.5, "8": 10.0}

# Right-side quadrants in each arch (used to order teeth along the arch).
_RIGHT_QUADRANTS = {"1", "4"}

MAX_IPR_PER_CONTACT_MM = 0.5
CROWN_WIDTH_REFERENCE = "Average mesiodistal crown widths from odontometric literature (heuristic)."
SPACE_DATA_GAP = (
    "Space analysis uses population-average crown widths, not this patient's measured "
    "crowns; segmented per-tooth meshes would replace the estimate."
)


def crown_width(tooth_value: str) -> float:
    """Typical mesiodistal width (mm) for an FDI tooth value."""
    quadrant, position = tooth_value[0], tooth_value[1]
    table = _WIDTHS_MAXILLARY if quadrant in {"1", "2", "5", "6"} else _WIDTHS_MANDIBULAR
    return table.get(position, 7.0)


def _arch_order_key(tooth_value: str) -> float:
    """Sortable position from one end of the arch to the other (right -> left)."""
    quadrant, position = tooth_value[0], int(tooth_value[1])
    return -position if quadrant in _RIGHT_QUADRANTS else position


def _available_length(centroids: dict[str, tuple[float, float]]) -> float:
    """Arch length the dentition currently occupies: the center-to-center path
    along the arch plus a half crown width at each end (so it is comparable to the
    sum of full mesiodistal crown widths). Robust to arch curvature/depth."""
    ordered = sorted(centroids, key=_arch_order_key)
    if len(ordered) < 2:
        return 0.0
    path = sum(
        hypot(centroids[b][0] - centroids[a][0], centroids[b][1] - centroids[a][1])
        for a, b in zip(ordered, ordered[1:])
    )
    return path + crown_width(ordered[0]) / 2 + crown_width(ordered[-1]) / 2


class IprItem(BaseModel):
    tooth_a: str
    tooth_b: str
    amount_mm: float


class ArchAnalysis(BaseModel):
    corrections: dict[str, tuple[float, float]] = Field(default_factory=dict)
    required_mm: float = 0.0
    available_mm: float = 0.0
    discrepancy_mm: float = 0.0  # required - available; > 0 means crowding
    ipr_plan: list[IprItem] = Field(default_factory=list)
    residual_mm: float = 0.0
    reference: str = CROWN_WIDTH_REFERENCE
    data_gap: str = SPACE_DATA_GAP


def analyze_arch(centroids: dict[str, tuple[float, float]]) -> ArchAnalysis:
    """Analyze ONE arch's landmark centroids. Empty result for < 3 teeth."""
    if len(centroids) < 3:
        return ArchAnalysis()

    corrections = archform_corrections(centroids)
    required = sum(crown_width(t) for t in centroids)
    available = _available_length(centroids)
    discrepancy = required - available

    ipr_plan: list[IprItem] = []
    residual = max(0.0, discrepancy)
    if discrepancy > 0:
        ordered = sorted(centroids, key=_arch_order_key)
        contacts = list(zip(ordered, ordered[1:]))
        remaining = discrepancy
        for a, b in contacts:
            if remaining <= 1e-9:
                break
            amount = round(min(MAX_IPR_PER_CONTACT_MM, remaining), 3)
            if amount <= 0:
                continue
            ipr_plan.append(IprItem(tooth_a=a, tooth_b=b, amount_mm=amount))
            remaining -= amount
        residual = round(max(0.0, remaining), 3)

    return ArchAnalysis(
        corrections=corrections,
        required_mm=round(required, 3),
        available_mm=round(available, 3),
        discrepancy_mm=round(discrepancy, 3),
        ipr_plan=ipr_plan,
        residual_mm=residual,
    )
