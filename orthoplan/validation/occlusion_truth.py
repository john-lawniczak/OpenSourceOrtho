"""Synthetic opposing arches with a known occlusal gap, for the registration gate.

Builds two crown-surface patches facing each other in a shared frame whose true
occlusal relationship is known by construction, so a change to ``register_bite``
shows up as a measurable move instead of an unverifiable difference. The patch is a
rectangular dental footprint rather than a horseshoe: the registration math reads
only per-cell biting-surface heights and footprint overlap, so the simpler shape
gives exact, PHI-free truth without changing what is exercised.

The biting surfaces are placed at known heights: the lower arch's occlusal plane
(its highest z) at ``-gap/2`` and the upper arch's occlusal plane (its lowest z) at
``+gap/2``, so the true vertical clearance between them is exactly ``gap``. A small
gingival skirt below each occlusal plane gives the arch realistic vertical extent
without disturbing the biting-surface extreme.

Pure list math, deterministic, no numpy.
"""

from __future__ import annotations

from orthoplan.model.geometry import Vec3

# Footprint and sampling of the synthetic patch (mediolateral x, anteroposterior y).
# Sampled finer than the occlusal grid cell (~0.9 mm) so a shifted arch still shares
# cells with its opposite - real million-vertex scans are dense; the fixture mimics
# that so it exercises the registration math rather than a sparse-sampling artefact.
_WIDTH = 40.0
_DEPTH = 30.0
_X_SAMPLES = 130
_Y_SAMPLES = 98
# Vertical skirt below each occlusal plane so each arch has ~crown-height extent.
_SKIRT = 8.0


def build_occluding_arches(
    *, gap_mm: float = 0.0, midline_offset_mm: float = 0.0, separated: bool = False
) -> tuple[list[Vec3], list[Vec3], dict[str, float]]:
    """Two opposing arch patches with a known occlusal gap and midline offset.

    ``midline_offset_mm`` shifts the lower arch along x within the shared frame
    (an alignment-quality probe). ``separated`` instead drops the lower arch into a
    disjoint frame (off-footprint in x and far below in z) to exercise the estimated
    alignment path. Returns ``(upper_vertices, lower_vertices, truth)``.
    """

    lower_x_shift = 200.0 if separated else midline_offset_mm
    lower_z_shift = -100.0 if separated else 0.0
    upper: list[Vec3] = []
    lower: list[Vec3] = []
    for i in range(_X_SAMPLES):
        x = -_WIDTH / 2.0 + _WIDTH * i / (_X_SAMPLES - 1)
        for j in range(_Y_SAMPLES):
            y = -_DEPTH / 2.0 + _DEPTH * j / (_Y_SAMPLES - 1)
            # Upper: occlusal plane (lowest z) at +gap/2, body rising above it.
            upper.append((x, y, gap_mm / 2.0))
            upper.append((x, y, gap_mm / 2.0 + _SKIRT))
            # Lower: occlusal plane (highest z) at -gap/2, body falling below it.
            lx = x + lower_x_shift
            lower.append((lx, y, -gap_mm / 2.0 + lower_z_shift))
            lower.append((lx, y, -gap_mm / 2.0 - _SKIRT + lower_z_shift))
    truth = {"gap_mm": float(gap_mm), "midline_offset_mm": float(0.0 if separated else midline_offset_mm)}
    return upper, lower, truth
