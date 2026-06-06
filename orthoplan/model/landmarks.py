"""Per-tooth crown landmarks read from a scan.

A landmark is an operator-identified crown center in the occlusal plane (the x/y
of the canonical scan frame; see ``model/geometry.py``). Landmarks are how the
generator grounds movement targets in the patient's ACTUAL tooth positions
instead of authored guesses - without needing full per-tooth segmentation.

Honesty: ``approximate`` defaults to True. Scaffolded/estimated landmarks must
keep it True so the UI and reports never present them as precise measurements.
Landmarks describe visible crown position only; they say nothing about roots,
bone, or occlusion.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.identity import Arch, ToothId


class CrownLandmark(BaseModel):
    """One tooth's crown center in occlusal-plane millimeters."""

    tooth: ToothId
    x_mm: float
    y_mm: float
    z_mm: float = 0.0
    approximate: bool = True
    source: str = "operator-identified"

    @property
    def arch(self) -> Arch:
        return self.tooth.arch


class ArchLandmarks(BaseModel):
    """A set of crown landmarks across one or both arches."""

    landmarks: list[CrownLandmark] = Field(default_factory=list)

    @property
    def approximate(self) -> bool:
        """True if ANY landmark is approximate (the conservative provenance)."""
        return any(lm.approximate for lm in self.landmarks)

    def by_arch(self) -> dict[Arch, list[CrownLandmark]]:
        grouped: dict[Arch, list[CrownLandmark]] = {}
        for lm in self.landmarks:
            grouped.setdefault(lm.arch, []).append(lm)
        return grouped

    def centroids(self) -> dict[str, tuple[float, float]]:
        """Occlusal-plane (x, y) centroid per FDI tooth value."""
        return {lm.tooth.value: (lm.x_mm, lm.y_mm) for lm in self.landmarks}
