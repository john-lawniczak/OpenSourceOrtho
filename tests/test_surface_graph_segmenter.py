"""Tests for the optional surface-graph segmentation candidate.

``SurfaceGraphSegmenter`` had no dedicated test coverage before this file, and
the shared synthetic-arch measurement lab (``orthoplan.validation.segmentation_cases``)
cannot gate it: ``build_synthetic_arch`` places one tiny, ISOLATED triangle per
sample point (see ``synthetic_arch.py``'s ``_place_tooth`` - each sampled point
gets its own fixed-offset micro-triangle with no shared edges to its
neighbours), so it has no real shared-edge topology for the Dijkstra-based
seed propagation in ``topology.propagate_seeds`` to traverse. Running the
candidate on that fixture silently collapses every region to its single seed
triangle - not a bug in the segmenter, a fixture mismatch. Do not "fix" this
by trying to make ``SurfaceGraphSegmenter`` pass on ``build_synthetic_arch``;
fix or extend the fixture instead, or keep using genuinely connected meshes
(a hand-built strip, or the real bundled scans) as done here.
"""

from __future__ import annotations

import time

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from orthoplan.datasets import SAMPLE_CASE_DIR  # noqa: E402
from orthoplan.io.stl_import import read_stl_geometry  # noqa: E402
from orthoplan.segmentation.heuristic import ToothSegment, default_arch_order  # noqa: E402
from orthoplan.segmentation.surface_graph import (  # noqa: E402
    SurfaceGraphSegmenter,
    draft_face_labels,
    refine_draft_labels,
)
from orthoplan.validation.segmentation_compactness import score_compactness  # noqa: E402

_SCAN_DIR = SAMPLE_CASE_DIR
_TIME_BUDGET_S = 30.0


def _connected_strip(n_quads: int) -> "np.ndarray":
    """A flat, genuinely shared-edge strip mesh: ``n_quads`` quads (2 faces each).

    Adjacent faces share BIT-IDENTICAL vertex coordinates (unlike the synthetic
    arch), so ``topology.face_graph`` can find real edges between them.
    """

    faces = []
    for x in range(n_quads):
        a, b, c, d = [x, 0, 0], [x + 1, 0, 0], [x, 1, 0], [x + 1, 1, 0]
        faces.extend([[a, b, c], [b, d, c]])
    return np.array(faces, dtype=float)


def test_refine_draft_labels_recovers_multi_triangle_regions_on_connected_mesh():
    """The refinement step must not collapse a tooth's region to its seed alone.

    Builds a small connected strip, hand-labels the first half as tooth "11"
    and the second half as tooth "12" (bypassing hybrid arch-detection, which
    is not under test here), and checks that propagation actually grows each
    seed back out to (most of) its true half - not just the seed triangle.
    """

    mesh = _connected_strip(8)  # 16 faces total
    drafts = [
        ToothSegment("11", [tuple(map(tuple, f)) for f in mesh[:8]], (0, 0, 0), 0.9),
        ToothSegment("12", [tuple(map(tuple, f)) for f in mesh[8:]], (0, 0, 0), 0.9),
    ]

    labels = draft_face_labels(mesh, drafts)
    assert set(labels[:8].tolist()) == {11}
    assert set(labels[8:].tolist()) == {12}

    refined = refine_draft_labels(mesh, labels)

    # The known failure mode: every region collapses to its single seed face.
    # A healthy refinement recovers most of each half, not just one triangle.
    # This strip is flat and uniform (no height/crease cue at the midpoint), so
    # the single boundary face can legitimately go either way - assert most of
    # each half is recovered, not pixel-perfect placement on an ambiguous edge.
    assert (refined[:8] == 11).sum() >= 7, "tooth 11 region collapsed toward its seed"
    assert (refined[8:] == 12).sum() >= 7, "tooth 12 region collapsed toward its seed"
    # No contamination beyond that single ambiguous boundary face.
    assert (refined[:8] == 12).sum() <= 1
    assert (refined[8:] == 11).sum() <= 1


@pytest.mark.parametrize(
    "filename,arch",
    [("initial-upper.stl", "maxillary"), ("initial-lower.stl", "mandibular")],
)
def test_real_scan_segments_within_plausible_bounds(filename: str, arch: str) -> None:
    """Sim-to-real smoke check, mirroring test_segmentation_real_scan.py's active-
    segmenter version but exercising SurfaceGraphSegmenter directly (it is not
    the active backend behind ``load_local_segmenter()``)."""

    path = _SCAN_DIR / filename
    if not path.is_file():
        pytest.skip(f"bundled scan not present: {path}")

    _asset, vertices = read_stl_geometry(path)

    start = time.monotonic()
    segments = SurfaceGraphSegmenter().segment(vertices, arch=arch)
    elapsed = time.monotonic() - start

    canonical = len(default_arch_order(arch))

    assert elapsed < _TIME_BUDGET_S, f"{arch} segmentation took {elapsed:.1f}s"
    assert segments, f"{arch}: segmenter returned no crowns"
    assert len(segments) <= canonical, f"{arch}: {len(segments)} crowns exceeds a full arch"

    labels = [s.tooth_value for s in segments]
    assert len(labels) == len(set(labels)), f"{arch}: duplicate labels {labels}"
    assert set(labels) <= set(default_arch_order(arch)), f"{arch}: off-arch labels {labels}"

    for segment in segments:
        assert 0.0 <= segment.confidence <= 1.0, f"{arch}: bad confidence {segment.confidence}"
    assert all(s.triangles for s in segments)

    # The known failure mode on a disconnected fixture: every region collapses
    # to its seed. On real (connected) geometry this must not happen.
    smallest = min(len(s.triangles) for s in segments)
    assert smallest > 1, f"{arch}: a region collapsed to {smallest} triangle(s)"


# Real-scan compactness floors, measured on the bundled canonical sample
# (2026-11-19). Set just below the observed baseline, same convention as
# segmentation_compactness_case.py: a sprawl regression trips the gate, a
# genuine tightening passes and shows the gain in the recorded metrics.
_REAL_COMPACTNESS_FLOORS = {
    "maxillary": {"mean": 0.38, "min": 0.24},
    "mandibular": {"mean": 0.42, "min": 0.34},
}


@pytest.mark.parametrize(
    "filename,arch",
    [("initial-upper.stl", "maxillary"), ("initial-lower.stl", "mandibular")],
)
def test_real_scan_compactness_does_not_regress(filename: str, arch: str) -> None:
    path = _SCAN_DIR / filename
    if not path.is_file():
        pytest.skip(f"bundled scan not present: {path}")

    _asset, vertices = read_stl_geometry(path)
    segments = SurfaceGraphSegmenter().segment(vertices, arch=arch)
    expected_count = len(default_arch_order(arch))
    score = score_compactness(segments, expected_count=expected_count)

    floor = _REAL_COMPACTNESS_FLOORS[arch]
    assert score.mean_compactness >= floor["mean"], (
        f"{arch} mean compactness regressed: {score.mean_compactness} < {floor['mean']}"
    )
    assert score.min_compactness >= floor["min"], (
        f"{arch} min compactness regressed: {score.min_compactness} < {floor['min']}"
    )
