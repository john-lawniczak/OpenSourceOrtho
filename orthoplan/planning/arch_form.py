"""Deterministic arch-form straightening corrections from visible crown geometry.

This is geometric processing of the crown positions that are ALREADY in the
scan - it never infers unseen anatomy (roots, bone) and never decides whether a
correction is clinically appropriate. The notion of "straighter" used here is
purely geometric: teeth that lie on a smooth fitted arch curve are treated as
aligned, and each tooth is moved toward that curve.

Axis convention (see ``model/geometry.py``): in the canonical ``scan-local``
frame ``z`` is vertical (occlusogingival) and ``x``/``y`` span the occlusal
plane. Corrections are computed in the occlusal plane only; ``z`` is left
untouched. Because the per-tooth mesiodistal/buccolingual mapping of x/y is not
resolved, this is explicitly a scan-axis heuristic, not a clinical measurement.
"""

from __future__ import annotations

# Per-tooth corrective translation is clamped so a poor fit cannot propose a
# wildly large move (which would also explode the staged step count).
MAX_CORRECTION_MM = 4.0


def fit_parabola(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Least-squares fit ``y = a*x^2 + b*x + c``; needs >= 3 distinct points.

    Solves the 3x3 normal equations directly (no numpy dependency). Raises
    ``ValueError`` if the system is singular (e.g. collinear sampling).
    """

    if len(xs) < 3:
        raise ValueError("parabola fit needs at least 3 points")
    s0 = float(len(xs))
    s1 = sum(xs)
    s2 = sum(x * x for x in xs)
    s3 = sum(x**3 for x in xs)
    s4 = sum(x**4 for x in xs)
    t0 = sum(ys)
    t1 = sum(x * y for x, y in zip(xs, ys))
    t2 = sum(x * x * y for x, y in zip(xs, ys))
    # Normal-equation matrix for [a, b, c] (rows correspond to s4/s3/s2 ...).
    matrix = [
        [s4, s3, s2, t2],
        [s3, s2, s1, t1],
        [s2, s1, s0, t0],
    ]
    return _solve3(matrix)


def _solve3(m: list[list[float]]) -> tuple[float, float, float]:
    """Gaussian elimination with partial pivoting on a 3x4 augmented matrix."""

    for col in range(3):
        pivot_row = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot_row][col]) < 1e-12:
            raise ValueError("singular system; cannot fit arch curve")
        m[col], m[pivot_row] = m[pivot_row], m[col]
        pivot = m[col][col]
        m[col] = [v / pivot for v in m[col]]
        for r in range(3):
            if r != col:
                factor = m[r][col]
                m[r] = [v - factor * mc for v, mc in zip(m[r], m[col])]
    return m[0][3], m[1][3], m[2][3]


def _clamp(value: float) -> float:
    return max(-MAX_CORRECTION_MM, min(MAX_CORRECTION_MM, value))


def archform_corrections(
    centroids: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """Return per-tooth ``(dx, dy)`` moves onto a fitted arch curve.

    ``centroids`` maps a tooth value to its occlusal-plane ``(x, y)`` position.
    The independent axis is the one with the larger spread (the arch-width
    direction); the dependent coordinate is moved onto the fitted parabola. The
    independent coordinate is left unchanged. Returns an empty dict when fewer
    than 3 teeth are available or the curve cannot be fit.
    """

    if len(centroids) < 3:
        return {}
    teeth = list(centroids)
    xs = [centroids[t][0] for t in teeth]
    ys = [centroids[t][1] for t in teeth]
    x_spread = max(xs) - min(xs)
    y_spread = max(ys) - min(ys)
    # Fit dependent = f(independent), where independent is the wider axis.
    indep, dep = (xs, ys) if x_spread >= y_spread else (ys, xs)
    try:
        a, b, c = fit_parabola(indep, dep)
    except ValueError:
        return {}

    corrections: dict[str, tuple[float, float]] = {}
    for tooth, ix, dv in zip(teeth, indep, dep):
        target = a * ix * ix + b * ix + c
        move = _clamp(target - dv)
        if x_spread >= y_spread:
            corrections[tooth] = (0.0, move)  # dependent was y
        else:
            corrections[tooth] = (move, 0.0)  # dependent was x
    return corrections
