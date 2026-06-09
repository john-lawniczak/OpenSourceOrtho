"""Optional learned (ONNX) segmenter: contract, loader preference, and fallback.

Phase 1 ships no model, so these tests prove the *contract and the inert fallback*,
not real inference: the learned backend stays out of the way when its extra/weights
are absent (the heuristic remains the default), and its label -> ToothSegment
mapping is exercised through an injected fake runner (no onnxruntime, no weights).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orthoplan.model.geometry import Vec3
from orthoplan.segmentation import learned
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.heuristic import default_arch_order
from orthoplan.segmentation.learned import (
    LearnedMeshSegmenter,
    SegmenterUnavailable,
    build_cell_features,
    load_learned_segmenter,
    resolve_weights_by_arch,
    segments_from_labels,
)
from orthoplan.segmentation_api import _segmenter_metadata


def _triangle_vertices(count: int) -> list[Vec3]:
    """``count`` triangles laid out so each has a distinct, non-degenerate position."""

    vertices: list[Vec3] = []
    for i in range(count):
        vertices.extend([(float(i), 0.0, 0.0), (float(i) + 0.5, 0.0, 0.0), (float(i), 0.5, 0.3)])
    return vertices


# --- Weights resolution / availability (the inert signal the loader catches) ------


def test_resolve_weights_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENSOURCE_ORTHO_SEG_WEIGHTS", raising=False)
    with pytest.raises(SegmenterUnavailable):
        resolve_weights_by_arch()


def test_resolve_weights_raises_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(SegmenterUnavailable):
        resolve_weights_by_arch(tmp_path / "nope.onnx")


def test_resolve_weights_single_file_serves_both_arches(tmp_path: Path) -> None:
    weights = tmp_path / "model.onnx"
    weights.write_bytes(b"not a real model")
    resolved = resolve_weights_by_arch(weights)
    assert resolved == {"maxillary": weights, "mandibular": weights}


def test_resolve_weights_directory_requires_both_arches(tmp_path: Path) -> None:
    (tmp_path / "maxillary.onnx").write_bytes(b"x")
    with pytest.raises(SegmenterUnavailable):  # mandibular.onnx missing
        resolve_weights_by_arch(tmp_path)
    (tmp_path / "mandibular.onnx").write_bytes(b"x")
    resolved = resolve_weights_by_arch(tmp_path)
    assert resolved["maxillary"].name == "maxillary.onnx"
    assert resolved["mandibular"].name == "mandibular.onnx"


def test_load_learned_segmenter_uses_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    weights = tmp_path / "model.onnx"
    weights.write_bytes(b"x")
    monkeypatch.setenv("OPENSOURCE_ORTHO_SEG_WEIGHTS", str(weights))
    # A runner is injected so the onnxruntime install check is bypassed (Phase 1 has
    # no onnxruntime); weights still resolve from the env var.
    segmenter = load_learned_segmenter(runner=lambda *_: [])
    assert isinstance(segmenter, LearnedMeshSegmenter)
    assert segmenter.name == "learned-mesh-onnx" and segmenter.backend == "onnxruntime"


def test_load_learned_segmenter_unavailable_without_onnxruntime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    weights = tmp_path / "model.onnx"
    weights.write_bytes(b"x")
    monkeypatch.setattr(learned, "_onnxruntime_available", lambda: False)
    with pytest.raises(SegmenterUnavailable):
        load_learned_segmenter(weights)


# --- Loader preference + fallback -------------------------------------------------


def test_loader_falls_back_to_heuristic_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENSOURCE_ORTHO_SEG_WEIGHTS", raising=False)
    segmenter = load_local_segmenter()
    assert "hybrid" in segmenter.name  # the always-on fallback


def test_loader_prefers_learned_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = LearnedMeshSegmenter({"maxillary": Path("x")}, runner=lambda *_: [])
    monkeypatch.setattr(learned, "load_learned_segmenter", lambda *a, **k: sentinel)
    assert load_local_segmenter() is sentinel


def test_loader_swallows_broken_optional_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_a, **_k):
        raise RuntimeError("corrupt weights")

    monkeypatch.setattr(learned, "load_learned_segmenter", explode)
    # A broken optional backend must never take down segmentation.
    assert "hybrid" in load_local_segmenter().name


# --- The contract: labels -> ToothSegment ----------------------------------------


def test_segments_from_labels_drops_gingiva_and_maps_fdi() -> None:
    vertices = _triangle_vertices(5)
    facets = learned._facets(vertices)
    centroids = [learned._tri_centroid(t) for t in facets]
    # Class 0 = gingiva (dropped); 1 and 2 = teeth; 99 = out of range (dropped).
    labels = [0, 1, 1, 2, 99]
    order = default_arch_order("maxillary")
    segments = segments_from_labels(facets, centroids, labels, arch="maxillary")
    assert [s.tooth_value for s in segments] == [order[0], order[1]]
    assert len(segments[0].triangles) == 2 and len(segments[1].triangles) == 1
    assert all(0.0 <= s.confidence <= 1.0 for s in segments)


def test_segments_from_labels_honours_tooth_values_override() -> None:
    vertices = _triangle_vertices(3)
    facets = learned._facets(vertices)
    centroids = [learned._tri_centroid(t) for t in facets]
    segments = segments_from_labels(
        facets, centroids, [1, 2, 0], arch="maxillary", tooth_values=("A", "B", "C")
    )
    assert [s.tooth_value for s in segments] == ["A", "B"]


def test_segment_runs_injected_runner_end_to_end() -> None:
    vertices = _triangle_vertices(4)
    captured: dict[str, object] = {}

    def fake_runner(verts: list[Vec3], arch: str, weights_path: Path) -> list[int]:
        captured["arch"] = arch
        return [1, 1, 2, 0]

    segmenter = LearnedMeshSegmenter({"maxillary": Path("dummy.onnx")}, runner=fake_runner)
    segments = segmenter.segment(vertices, arch="maxillary")
    order = default_arch_order("maxillary")
    assert captured["arch"] == "maxillary"
    assert [s.tooth_value for s in segments] == [order[0], order[1]]


def test_segment_raises_for_unconfigured_arch() -> None:
    segmenter = LearnedMeshSegmenter({"maxillary": Path("dummy.onnx")}, runner=lambda *_: [])
    with pytest.raises(SegmenterUnavailable):
        segmenter.segment(_triangle_vertices(3), arch="mandibular")


def test_build_cell_features_are_fifteen_dim_per_face() -> None:
    vertices = _triangle_vertices(6)
    facets = learned._facets(vertices)
    centroids = [learned._tri_centroid(t) for t in facets]
    rows = build_cell_features(facets, centroids)
    assert len(rows) == len(facets)
    assert all(len(row) == learned._FEATURE_DIM for row in rows)


def test_metadata_surfaces_learned_backend() -> None:
    segmenter = LearnedMeshSegmenter({"maxillary": Path("x")}, runner=lambda *_: [])
    meta = _segmenter_metadata(segmenter)
    assert meta == {"name": "learned-mesh-onnx", "version": "0.1.0", "backend": "onnxruntime"}
