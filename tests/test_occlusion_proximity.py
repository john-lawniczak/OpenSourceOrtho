"""Occlusal proximity: per-cell clearance classified into review colour bands.

Pins the band thresholds, the as-scanned alignment gate (the overlay must only be
painted when its coordinates match the rendered scans), and the payload contract
the viewer consumes - including that it never raises and needs both arches.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orthoplan.occlusion.grid import build_occlusal_grid
from orthoplan.occlusion.proximity import (
    classify_proximity,
    proximity_map_to_dict,
)
from orthoplan.occlusion.proximity_api import proximity_payload
from orthoplan.occlusion.registration import register_bite
from orthoplan.validation.occlusion_truth import build_occluding_arches

_SCAN_DIR = Path(__file__).resolve().parents[1] / "ui" / "example-scans" / "canonical-orthocad-001"


def _classify(gap_mm: float):
    upper, lower, _truth = build_occluding_arches(gap_mm=gap_mm)
    reg = register_bite(upper, lower)
    grid = build_occlusal_grid(upper, lower, lower_offset=reg.lower_offset)
    return classify_proximity(grid, reg)


def test_clearance_maps_to_expected_band() -> None:
    # A uniform synthetic gap puts every shared cell in the same band.
    assert {c.band for c in _classify(0.2).cells} == {"contact"}  # <= 0.5
    assert {c.band for c in _classify(1.0).cells} == {"near"}  # 0.5 < c <= 1.5
    assert {c.band for c in _classify(2.5).cells} == {"clearance"}  # > 1.5


def test_as_scanned_map_is_aligned_and_counted() -> None:
    pmap = _classify(0.2)
    assert pmap.aligned_to_scan is True
    assert pmap.approximate is False
    assert pmap.counts["contact"] == len(pmap.cells) > 0


def test_estimated_alignment_is_not_painted_on_scans() -> None:
    upper, lower, _truth = build_occluding_arches(gap_mm=0.4, separated=True)
    reg = register_bite(upper, lower)
    grid = build_occlusal_grid(upper, lower, lower_offset=reg.lower_offset)
    pmap = classify_proximity(grid, reg)
    # An estimated alignment moved the lower arch, so its coordinates would not line
    # up with the unshifted rendered scans - the viewer must not paint it.
    assert reg.approximate is True
    assert pmap.aligned_to_scan is False


def test_map_dict_shape_for_the_viewer() -> None:
    payload = proximity_map_to_dict(_classify(1.0))
    assert set(payload) >= {"cell_size", "counts", "aligned_to_scan", "caveat", "cells"}
    assert "not bite force" in payload["caveat"].lower() or "not" in payload["caveat"].lower()
    cell = payload["cells"][0]
    assert set(cell) == {"x", "y", "z", "clearance", "band"}


def test_payload_requires_both_arches() -> None:
    result = proximity_payload(
        {"scans": [{"reference": "nope-upper.stl", "arch": "maxillary"}]}, ui_dir="ui"
    )
    assert result["ok"] is False
    assert result["errors"]


def test_payload_never_raises_on_bad_input() -> None:
    result = proximity_payload({"scans": "not-a-list"}, ui_dir="ui")
    assert result["ok"] is False


def test_payload_on_bundled_scans_is_as_scanned() -> None:
    upper = _SCAN_DIR / "sample-test-case-upper.stl"
    lower = _SCAN_DIR / "sample-test-case-lower.stl"
    if not (upper.is_file() and lower.is_file()):
        pytest.skip("bundled scans not present")

    result = proximity_payload(
        {
            "scans": [
                {"reference": f"example-scans/canonical-orthocad-001/{upper.name}", "arch": "maxillary"},
                {"reference": f"example-scans/canonical-orthocad-001/{lower.name}", "arch": "mandibular"},
            ],
            "units_confirmed": True,
        },
        ui_dir=_SCAN_DIR.parents[1],
    )
    assert result["ok"] is True
    assert result["registration"]["mode"] == "as-scanned"
    prox = result["proximity"]
    assert prox["aligned_to_scan"] is True
    total = sum(prox["counts"].values())
    assert total == len(prox["cells"]) > 0
    assert prox["counts"]["contact"] > 0  # real molars occlude somewhere
