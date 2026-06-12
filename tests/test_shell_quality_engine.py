"""Shell QA verification: an independent analytic oracle plus messy fixtures.

These tests check the shell builder and its QA against ground truth that does NOT
come from the builder itself: a closed-form slab volume (math, not our code) and
deliberately malformed geometry whose defects the QA must name. This is the
"known-good comparison + messy corpus" the maturity doc calls for, without any
external mesh pipeline or PHI.
"""

from __future__ import annotations

import time

import pytest

from orthoplan.aligner_shell import build_aligner_shell
from orthoplan.print_aligner import _failed_checks, _quality_block

# Unit quad in z=0 with +z winding; its outward-offset shell is an analytic slab.
_QUAD = [
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)),
    ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
]


def _signed_volume(triangles) -> float:
    """Divergence-theorem volume of a closed triangle mesh (independent oracle)."""

    total = 0.0
    for a, b, c in triangles:
        total += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    return total


def test_flat_quad_shell_matches_closed_form_slab_volume() -> None:
    # A 1x1 quad offset by 0.6mm encloses exactly area*thickness = 0.6 mm^3.
    result = build_aligner_shell(_QUAD, thickness_mm=0.6)
    assert abs(_signed_volume(result.triangles)) == pytest.approx(0.6, abs=1e-6)


def test_z_compensation_translates_the_flat_slab_without_changing_volume() -> None:
    # When every input normal is parallel (a flat surface), compensation is a
    # pure rigid translation: the slab moves but its enclosed volume is invariant.
    base = build_aligner_shell(_QUAD, thickness_mm=0.6)
    shifted = build_aligner_shell(_QUAD, thickness_mm=0.6, z_compensation_mm=0.2)
    assert abs(_signed_volume(shifted.triangles)) == pytest.approx(
        abs(_signed_volume(base.triangles)), abs=1e-6
    )
    base_min_z = min(v[2] for tri in base.triangles for v in tri)
    shifted_min_z = min(v[2] for tri in shifted.triangles for v in tri)
    assert shifted_min_z == pytest.approx(base_min_z + 0.2, abs=1e-6)


def test_known_good_slab_passes_every_qa_check() -> None:
    stats = build_aligner_shell(_QUAD, thickness_mm=0.6).stats
    block = _quality_block(stats)
    assert block["verdict"] == "CONSISTENT"
    assert block["failed_checks"] == []
    assert block["self_intersection_count"] == 0
    assert block["nonmanifold_edge_count"] == 0
    assert block["watertight"] is True


def test_disconnected_islands_are_reported_with_a_named_reason() -> None:
    shifted = [
        tuple((v[0] + 5.0, v[1], v[2]) for v in tri)  # type: ignore[misc]
        for tri in _QUAD
    ]
    stats = build_aligner_shell([*_QUAD, *shifted], thickness_mm=0.5).stats
    block = _quality_block(stats)
    assert block["verdict"] == "ISSUES"
    assert any("disconnected" in reason for reason in block["failed_checks"])


def test_failed_checks_names_self_intersection_and_nonmanifold_defects() -> None:
    base = build_aligner_shell(_QUAD, thickness_mm=0.6).stats
    bad = base.model_copy(update={"self_intersection_count": 3, "nonmanifold_edge_count": 2})
    reasons = _failed_checks(bad)
    assert any("self-intersecting triangles: 3" in reason for reason in reasons)
    assert any("nonmanifold edges: 2" in reason for reason in reasons)


def test_failed_checks_names_thin_walls_below_minimum_feature() -> None:
    base = build_aligner_shell(_QUAD, thickness_mm=0.6).stats
    thin = base.model_copy(update={"min_thickness_mm": 0.1, "minimum_printable_feature_mm": 0.3})
    reasons = _failed_checks(thin)
    assert any("min wall thickness" in reason for reason in reasons)


def test_full_arch_scale_shell_qa_stays_within_wall_clock_budget() -> None:
    surface = _arch_surface(cols=72, rows=28, spacing=0.45)

    start = time.perf_counter()
    result = build_aligner_shell(surface, thickness_mm=0.6)
    elapsed = time.perf_counter() - start

    assert result.stats.triangle_count >= 8_000
    assert result.stats.self_intersection_count == 0
    assert result.stats.inner_outer_min_clearance_mm == pytest.approx(0.6, abs=1e-6)
    assert elapsed < 5.0


def _arch_surface(*, cols: int, rows: int, spacing: float) -> list:
    points = [
        [
            (
                (col - cols / 2) * spacing,
                (row - rows / 2) * spacing,
                0.08 * ((col - cols / 2) * spacing) ** 2,
            )
            for col in range(cols + 1)
        ]
        for row in range(rows + 1)
    ]
    triangles = []
    for row in range(rows):
        for col in range(cols):
            a = points[row][col]
            b = points[row][col + 1]
            c = points[row + 1][col]
            d = points[row + 1][col + 1]
            triangles.append((a, b, d))
            triangles.append((a, d, c))
    return triangles
