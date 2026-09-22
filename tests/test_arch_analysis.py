from __future__ import annotations

from orthoplan.planning.arch_analysis import (
    MAX_IPR_PER_CONTACT_MM,
    analyze_arch,
    crown_width,
)


def _on_curve(xs: list[float]) -> dict[str, tuple[float, float]]:
    # y = 0.01 x^2 ; teeth 13,12,11,21,22 placed exactly on the curve.
    teeth = ["13", "12", "11", "21", "22"]
    return {t: (x, round(0.01 * x * x, 4)) for t, x in zip(teeth, xs)}


def test_on_curve_teeth_need_almost_no_correction() -> None:
    centroids = _on_curve([-16, -8, 0, 8, 16])
    analysis = analyze_arch(centroids)
    for dx, dy in analysis.corrections.values():
        assert abs(dx) < 1e-6 and abs(dy) < 1e-6


def test_off_curve_tooth_gets_the_largest_correction() -> None:
    centroids = _on_curve([-16, -8, 0, 8, 16])
    centroids["11"] = (0.0, 2.0)  # pull the central incisor off the arch
    analysis = analyze_arch(centroids)
    moved = max(abs(analysis.corrections["11"][0]), abs(analysis.corrections["11"][1]))
    others = max(
        max(abs(dx), abs(dy)) for t, (dx, dy) in analysis.corrections.items() if t != "11"
    )
    assert moved > others
    assert moved > 1.0  # roughly returns it toward the curve


def test_crowding_produces_capped_ipr_within_discrepancy() -> None:
    # A tight arch: teeth packed far closer than their crown widths require.
    tight = {"13": (-6, 1.2), "12": (-4, 0.6), "11": (-2, 0.2), "21": (0, 0.0), "22": (2, 0.2)}
    analysis = analyze_arch(tight)
    assert analysis.discrepancy_mm > 0
    assert analysis.ipr_plan
    assert all(item.amount_mm <= MAX_IPR_PER_CONTACT_MM + 1e-9 for item in analysis.ipr_plan)
    ipr_total = sum(item.amount_mm for item in analysis.ipr_plan)
    assert ipr_total <= analysis.discrepancy_mm + 1e-6
    assert abs(analysis.residual_mm - (analysis.discrepancy_mm - ipr_total)) < 1e-3


def test_tighter_arch_has_more_crowding_than_spaced() -> None:
    tight = {"13": (-6, 1.2), "12": (-4, 0.6), "11": (-2, 0.2), "21": (0, 0.0)}
    spaced = {"13": (-21, 2.4), "12": (-14, 1.0), "11": (-7, 0.3), "21": (0, 0.0)}
    assert analyze_arch(tight).discrepancy_mm > analyze_arch(spaced).discrepancy_mm


def test_few_teeth_yield_empty_analysis() -> None:
    analysis = analyze_arch({"11": (0, 0), "21": (8, 0)})
    assert analysis.corrections == {}
    assert analysis.discrepancy_mm == 0.0
    assert analysis.ipr_plan == []


def test_crown_width_known_values() -> None:
    assert crown_width("11") == 8.5  # maxillary central incisor
    assert crown_width("36") == 11.0  # mandibular first molar
