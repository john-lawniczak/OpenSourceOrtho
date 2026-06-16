from __future__ import annotations

from pathlib import Path

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.heuristic import ToothSegment, _facets, default_arch_order
from orthoplan.segmentation.quality import evaluate_segmentation_quality
from orthoplan.validation.segmentation_truth import build_synthetic_arch, full_arch_truth


def test_perfect_synthetic_segments_clear_production_gate() -> None:
    arch = build_synthetic_arch(full_arch_truth("maxillary"))
    by_tooth: dict[str, list] = {tooth: [] for tooth in arch.tooth_values}
    for tri in _facets(arch.vertices):
        centroid = (
            (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
            (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
            (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
        )
        key = (round(centroid[0] * 1e6), round(centroid[1] * 1e6), round(centroid[2] * 1e6))
        by_tooth[arch.truth_by_centroid[key]].append(tri)
    segments = []
    for tooth, tris in by_tooth.items():
        centroids = [
            (
                (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
                (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
                (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
            )
            for tri in tris
        ]
        center = (
            sum(point[0] for point in centroids) / len(centroids),
            sum(point[1] for point in centroids) / len(centroids),
            sum(point[2] for point in centroids) / len(centroids),
        )
        segments.append(ToothSegment(tooth_value=tooth, triangles=tris, centroid=center, confidence=0.95))

    report = evaluate_segmentation_quality(segments, arch="maxillary")

    assert report.reviewable is True
    assert report.production_candidate is True
    assert report.failed_checks == []
    assert report.production_blockers == []


def test_current_real_scan_heuristic_is_reviewable_but_not_production_candidate() -> None:
    scan = (
        Path(__file__).resolve().parents[1]
        / "ui/example-scans/canonical-orthocad-001/sample-test-case-upper.stl"
    )
    _asset, vertices = read_stl_geometry(scan)
    segments = load_local_segmenter().segment(vertices, arch="maxillary")

    report = evaluate_segmentation_quality(segments, arch="maxillary")

    assert report.observed_tooth_count == len(default_arch_order("maxillary"))
    assert report.reviewable is True
    assert report.production_candidate is False
    assert "mean-compactness-below-production-floor" in report.production_blockers
