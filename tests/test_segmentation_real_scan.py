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

Observed at the time of writing (crown-peak counting):
- mandibular (lower): 14 / 14 crowns - correct, confidence ~0.5-0.85.
- maxillary (upper): 7 / 14 crowns - a real UNDERCOUNT. The upper scan's occlusal
  height profile (palate, crown orientation) does not present 14 clean peaks, so
  the counter tuned on synthetic arches misses about half. Closing that gap is the
  tracked follow-up; this test guards against gross regression in the meantime.
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


def test_lower_arch_is_counted_well_on_real_geometry() -> None:
    """The mandibular scan is the working real-data case: most of a full arch.

    This guards the case that already survives real geometry, so a future change
    that breaks real-scan counting (e.g. an over-aggressive peak threshold) is
    caught even though the upper scan's gap is not yet closed.
    """

    path = _SCAN_DIR / "sample-test-case-lower.stl"
    if not path.is_file():
        pytest.skip(f"bundled scan not present: {path}")

    _asset, vertices = read_stl_geometry(path)
    segments = load_local_segmenter().segment(vertices, arch="mandibular")
    # Most of a 14-tooth arch should be recovered on this clean lower scan.
    assert len(segments) >= 12, f"mandibular regressed: detected {len(segments)} crowns"
