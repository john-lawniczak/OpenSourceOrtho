"""Synthetic whole-arch mesh construction with known per-triangle ground truth.

Builds a placed horseshoe of cosine crowns whose tooth membership is known by
construction, so the segmenter can be scored against exact, PHI-free truth (see
``segmentation_truth`` for the scoring half). Realism knobs (uneven crown widths,
flat molar plateaus, height noise) push the arch toward real-scan difficulty.

Pure list math, no numpy, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import default_arch_order

# Horseshoe geometry for the synthetic arch. Teeth span less than a full turn so
# there is an explicit opening gap at the back (the segmenter's wrap-origin logic
# expects the largest angular gap to be the mouth opening, not an embrasure).
_ARCH_SPAN = 1.6 * pi
_RADIUS = 22.0
_CROWN_HEIGHT = 9.0
_VALLEY_HEIGHT = 3.0
# Open extraction sites are filled with a flat "gum" surface below the inter-crown
# valleys, so the hole reads as the deepest, widest valley on the arch.
_GUM_HEIGHT_RATIO = 0.4
# Triangles per tooth. Each tooth's triangles span the inner 90% of its sector,
# leaving a 10% no-triangle embrasure so a height valley forms between crowns.
_TRIS_PER_TOOTH = 16
_SECTOR_FILL = 0.9
# A tiny in-plane triangle whose three offsets sum to zero, so its centroid is
# exactly the placed point and recomputing it (mean of vertices) is loss-free.
_TRI_OFFSETS: tuple[Vec3, ...] = (
    (0.06, 0.0, 0.0),
    (-0.03, 0.052, 0.0),
    (-0.03, -0.052, 0.0),
)
# Relative mesiodistal crown widths by FDI position (second digit): molars are far
# wider than incisors. Equal-sector placement hides the segmenter's real-scan
# weakness; a width-weighted arch tests whether cuts land on the true valleys.
_WIDTH_BY_POSITION = {
    "1": 0.78, "2": 0.66, "3": 0.92, "4": 1.0, "5": 1.0, "6": 1.45, "7": 1.4, "8": 1.3,
}


def _centroid_key(point: Vec3) -> tuple[int, int, int]:
    """Hashable identity for a triangle centroid, robust to float noise."""

    return (round(point[0] * 1e6), round(point[1] * 1e6), round(point[2] * 1e6))


def _jitter(i: int, t: int) -> float:
    """Deterministic per-triangle height jitter in [-1, 1) (no RNG, CI-stable)."""

    h = (i * 73856093) ^ (t * 19349663)
    return ((h % 2000) / 1000.0) - 1.0


def _crown_height(
    frac: float, valley_height: float, crown_height: float, occlusal_flat: float
) -> float:
    """Cosine crown profile, optionally clipped to a flat occlusal plateau.

    ``frac`` is the in-sector position in [-0.5, 0.5]. With ``occlusal_flat`` the
    central band is a flat table at ``crown_height`` (a molar's occlusal surface)
    and only the cusp slopes fall to the embrasure valley, so wide adjacent crowns
    merge into one broad peak - the real under-counting case.
    """

    relief = crown_height - valley_height
    flat_half = max(0.0, min(occlusal_flat, 0.96)) / 2.0
    edge = abs(frac)
    if edge <= flat_half:
        return crown_height
    slope_span = max(1e-9, 0.5 - flat_half)
    u = (edge - flat_half) / slope_span  # 0 at plateau edge -> 1 at the valley
    return valley_height + relief * cos(u * (pi / 2.0))


@dataclass(frozen=True)
class SyntheticArch:
    """A placed whole-arch mesh plus the true tooth label of every triangle."""

    vertices: list[Vec3]
    # True tooth value keyed by triangle-centroid identity.
    truth_by_centroid: dict[tuple[int, int, int], str]
    tooth_values: tuple[str, ...]
    # True center arc-position (radians from the arch origin) per tooth value.
    arc_center: dict[str, float]

    @property
    def expected_count(self) -> int:
        return len(self.tooth_values)


@dataclass(frozen=True)
class _ArchShape:
    """Crown-geometry knobs shared by every tooth placed on one synthetic arch."""

    radius: float
    crown_height: float
    valley_height: float
    tris_per_tooth: int
    occlusal_flat: float
    noise: float
    gum_height: float


def realistic_widths(tooth_values: tuple[str, ...]) -> tuple[float, ...]:
    """Relative crown widths for ``tooth_values`` (molars wide, incisors narrow)."""

    return tuple(_WIDTH_BY_POSITION.get(str(tooth)[-1], 1.0) for tooth in tooth_values)


def full_arch_truth(arch: ArchName) -> tuple[str, ...]:
    """The canonical FDI tooth order the segmenter labels for a full arch."""

    return default_arch_order(arch)


def _place_tooth(
    index: int,
    tooth: str,
    center: float,
    sector: float,
    *,
    is_gap: bool,
    shape: _ArchShape,
    vertices: list[Vec3],
    truth: dict[tuple[int, int, int], str],
) -> None:
    """Append one tooth's triangle cluster and record its per-centroid truth."""

    half = 0.5 * _SECTOR_FILL * sector
    tris = shape.tris_per_tooth
    relief = shape.crown_height - shape.valley_height
    for t in range(tris):
        frac = (t / (tris - 1)) - 0.5 if tris > 1 else 0.0  # in-sector pos [-0.5, 0.5]
        theta = center + frac * 2.0 * half
        if is_gap:
            height = shape.gum_height
        else:
            height = _crown_height(frac, shape.valley_height, shape.crown_height, shape.occlusal_flat)
            if shape.noise:
                height += relief * shape.noise * _jitter(index, t)
        cx, cy = shape.radius * cos(theta), shape.radius * sin(theta)
        if not is_gap:
            truth[_centroid_key((cx, cy, height))] = tooth
        for off in _TRI_OFFSETS:
            vertices.append((cx + off[0], cy + off[1], height + off[2]))


def build_synthetic_arch(
    tooth_values: tuple[str, ...],
    *,
    gaps: tuple[str, ...] = (),
    radius: float = _RADIUS,
    crown_height: float = _CROWN_HEIGHT,
    valley_height: float = _VALLEY_HEIGHT,
    tris_per_tooth: int = _TRIS_PER_TOOTH,
    sector_weights: tuple[float, ...] | None = None,
    occlusal_flat: float = 0.0,
    noise: float = 0.0,
) -> SyntheticArch:
    """Place ``tooth_values`` as cosine crowns around a horseshoe.

    Each tooth is a triangle cluster at a known arc sector; height peaks at the
    sector center and dips to ``valley_height`` at the embrasures, so the gaps read
    as valleys to the segmenter. ``gaps`` models an open extraction site (a flat
    gum-filled hole with no crown peak and no ground-truth label).

    Realism knobs that push the arch toward a real scan: ``sector_weights`` give
    teeth uneven widths (see :func:`realistic_widths`); ``occlusal_flat`` (0..1)
    clips crowns into flat molar plateaus that tempt under-counting; ``noise`` adds
    deterministic per-triangle height jitter. They let a segmenter change prove a
    gain on the hard case instead of only the pristine one.
    """

    n = len(tooth_values)
    weights = sector_weights if sector_weights is not None else (1.0,) * n
    if len(weights) != n:
        raise ValueError("sector_weights must match tooth_values length")
    total_weight = sum(weights)
    widths = [_ARCH_SPAN * w / total_weight for w in weights]
    starts = [-_ARCH_SPAN / 2.0 + sum(widths[:i]) for i in range(n)]
    gap_set = set(gaps)
    shape = _ArchShape(
        radius, crown_height, valley_height, tris_per_tooth,
        occlusal_flat, noise, valley_height * _GUM_HEIGHT_RATIO,
    )
    vertices: list[Vec3] = []
    truth: dict[tuple[int, int, int], str] = {}
    arc_center: dict[str, float] = {}
    present: list[str] = []

    for i, tooth in enumerate(tooth_values):
        center = starts[i] + 0.5 * widths[i]
        is_gap = tooth in gap_set
        _place_tooth(i, tooth, center, widths[i], is_gap=is_gap, shape=shape,
                     vertices=vertices, truth=truth)
        if not is_gap:
            arc_center[tooth] = center
            present.append(tooth)

    return SyntheticArch(
        vertices=vertices,
        truth_by_centroid=truth,
        tooth_values=tuple(present),
        arc_center=arc_center,
    )
