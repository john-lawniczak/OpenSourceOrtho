"""Sim-to-real smoke check: run the on-device segmenter on the bundled real scans.

Every other segmentation test runs on synthetic arches whose geometry is built to
present crowns as clean height peaks. This diagnostic runs the SAME active
segmenter on the real canonical sample scans (~990k / ~860k vertices) to answer
one question: does the synthetic-tuned algorithm survive real geometry?

It is deliberately a loose smoke check, not an accuracy gate (the scans are
unlabelled): it asserts the segmenter runs without crashing, finishes quickly,
returns a plausible number of crowns within the algorithm's own bounds, and
produces valid confidences. It also RECORDS the observed crown counts so the
current sim-to-real gap is visible and tracked.

Observed at the time of writing (crown-peak counting at fine resolution):
- mandibular (lower): 14 / 14 crowns - correct, confidence ~0.5-0.85.
- maxillary (upper): 12 / 14 crowns. The upper occlusal plane is flat across the
  posterior teeth (curve of Spee/Wilson, palate), so two adjacent crowns still
  merge into one height peak even at fine resolution - 12/14 is the realistic
  ceiling for 1-D height counting. (Counting at the original coarse resolution
  found only 7; the finer count profile recovered the other five.) The remaining
  two are a positional guess the user closes via mark-the-gap / re-anchor.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.heuristic import _MIN_DETECTED_TEETH, default_arch_order

_SCAN_DIR = Path(__file__).resolve().parents[1] / "ui" / "example-scans" / "canonical-orthocad-001"
_SCANS = [
    ("sample-test-case-upper.stl", "maxillary"),
    ("sample-test-case-lower.stl", "mandibular"),
]
# Generous budget: the real read+segment is well under a second, so anything near
# this means a pathological slowdown, not normal variance.
_TIME_BUDGET_S = 30.0


@pytest.mark.parametrize("filename,arch", _SCANS)
def test_real_scan_segments_within_plausible_bounds(filename: str, arch: str) -> None:
    path = _SCAN_DIR / filename
    if not path.is_file():
        pytest.skip(f"bundled scan not present: {path}")

    start = time.monotonic()
    _asset, vertices = read_stl_geometry(path)
    segments = load_local_segmenter().segment(vertices, arch=arch)
    elapsed = time.monotonic() - start

    canonical = len(default_arch_order(arch))

    # Does not crash / hang on real geometry.
    assert elapsed < _TIME_BUDGET_S, f"{arch} segmentation took {elapsed:.1f}s"
    assert segments, f"{arch}: segmenter returned no crowns"

    # Plausible crown count: within the algorithm's own [floor, canonical] bounds -
    # not zero, not more than a full arch. (This is a smoke bound, not an accuracy
    # claim; the upper scan currently lands at the low end - see module docstring.)
    assert _MIN_DETECTED_TEETH <= len(segments) <= canonical, (
        f"{arch}: detected {len(segments)} crowns, outside [{_MIN_DETECTED_TEETH}, {canonical}]"
    )

    # Labels are valid, in-arch FDI numbers with no duplicates.
    labels = [s.tooth_value for s in segments]
    assert len(labels) == len(set(labels)), f"{arch}: duplicate labels {labels}"
    assert set(labels) <= set(default_arch_order(arch)), f"{arch}: off-arch labels {labels}"

    # Confidences are well-formed.
    for segment in segments:
        assert 0.0 <= segment.confidence <= 1.0, f"{arch}: bad confidence {segment.confidence}"

    # Every crown carries geometry.
    assert all(s.triangles for s in segments)


# Real-data crown-count floors. These lock in the counts the fine-resolution
# crown-peak counter recovers, so a future change that regresses real-scan counting
# (e.g. an over-aggressive prominence threshold) is caught - even where the count
# is below a full arch because crowns genuinely merge in the 1-D height signal.
_REAL_COUNT_FLOOR = {"maxillary": 10, "mandibular": 12}


@pytest.mark.parametrize("filename,arch", _SCANS)
def test_real_scan_crown_count_does_not_regress(filename: str, arch: str) -> None:
    path = _SCAN_DIR / filename
    if not path.is_file():
        pytest.skip(f"bundled scan not present: {path}")

    _asset, vertices = read_stl_geometry(path)
    segments = load_local_segmenter().segment(vertices, arch=arch)
    floor = _REAL_COUNT_FLOOR[arch]
    assert len(segments) >= floor, (
        f"{arch} crown count regressed: detected {len(segments)}, floor {floor}"
    )
