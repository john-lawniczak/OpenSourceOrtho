"""Bite registration: trust the scanner's bite when present, estimate honestly otherwise.

These pin the two behaviours the opposing-arch features depend on: when arches
arrive already occluding (a real registered export) the registration is identity
and the metrics describe the real bite; when they arrive in separate frames it
falls back to a clearly-flagged approximate alignment that brings them to contact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orthoplan.occlusion import apply_registration, build_occlusal_grid, register_bite
from orthoplan.validation.occlusion_truth import build_occluding_arches


def test_as_scanned_pair_uses_identity_and_recovers_gap() -> None:
    upper, lower, truth = build_occluding_arches(gap_mm=0.6, midline_offset_mm=1.0)
    reg = register_bite(upper, lower)

    assert reg.mode == "as-scanned"
    assert reg.approximate is False
    assert reg.lower_offset == (0.0, 0.0, 0.0)  # the scanner's registration is trusted
    assert abs(reg.occlusal_gap_mm - truth["gap_mm"]) <= 0.15
    assert abs(reg.midline_offset_mm - truth["midline_offset_mm"]) <= 0.2
    assert reg.coverage >= 0.85
    assert reg.interpenetration_mm <= 0.5


def test_separated_pair_falls_back_to_estimated_alignment() -> None:
    upper, lower, _truth = build_occluding_arches(gap_mm=0.4, separated=True)
    reg = register_bite(upper, lower)

    assert reg.mode == "estimated"
    assert reg.approximate is True
    assert reg.lower_offset != (0.0, 0.0, 0.0)
    assert "APPROXIMATE" in reg.notes
    # Estimation centres the arches and brings them to first contact.
    moved = apply_registration(lower, reg)
    assert abs(max(p[2] for p in moved) - min(p[2] for p in upper)) <= 0.05
    assert reg.confidence < register_bite(*build_occluding_arches(gap_mm=0.4)[:2]).confidence


def test_missing_arch_is_unavailable_not_a_crash() -> None:
    upper, _lower, _truth = build_occluding_arches(gap_mm=0.4)
    reg = register_bite(upper, [])
    assert reg.mode == "unavailable"
    assert reg.confidence == 0.0


def test_unconfirmed_units_are_flagged_in_notes() -> None:
    upper, lower, _truth = build_occluding_arches(gap_mm=0.4)
    reg = register_bite(upper, lower, units_confirmed=False)
    assert "units are unconfirmed" in reg.notes.lower()


def test_extent_reports_registered_dentition_size() -> None:
    upper, lower, _truth = build_occluding_arches(gap_mm=0.4)
    reg = register_bite(upper, lower)
    width, depth, height = reg.extent_mm
    assert round(width) == 40 and round(depth) == 30  # the synthetic footprint
    assert height > 0


def test_occlusal_grid_clearance_signs() -> None:
    upper, lower, _truth = build_occluding_arches(gap_mm=1.0)
    grid = build_occlusal_grid(upper, lower)
    clearances = grid.clearances()
    assert clearances
    # Every shared cell sees the upper plane 1.0 above the lower plane (a clean gap).
    assert all(abs(c - 1.0) <= 1e-6 for c in clearances)
    assert grid.coverage() >= 0.85


def test_real_bundled_scans_register_as_scanned() -> None:
    scan_dir = Path(__file__).resolve().parents[1] / "ui" / "example-scans" / "canonical-orthocad-001"
    upper_path = scan_dir / "sample-test-case-upper.stl"
    lower_path = scan_dir / "sample-test-case-lower.stl"
    if not (upper_path.is_file() and lower_path.is_file()):
        pytest.skip("bundled scans not present")

    from orthoplan.io.stl_import import read_stl_geometry

    _au, upper = read_stl_geometry(upper_path)
    _al, lower = read_stl_geometry(lower_path)
    reg = register_bite(upper, lower)

    # The bundled OrthoCAD export already carries the scanner's bite registration.
    assert reg.mode == "as-scanned"
    assert reg.coverage >= 0.5
    assert reg.midline_offset_mm < 5.0
    # Real molars span ~50-65 mm mediolaterally; a sane registered extent, not a blowup.
    assert 40.0 < reg.extent_mm[0] < 90.0
