"""Real-scan segmentation quality-gate metrics."""

from __future__ import annotations

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID


from orthoplan.io.mesh_import import read_mesh_geometry
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.quality import evaluate_segmentation_quality
from orthoplan.validation.benchmark_models import BenchmarkMetric


def segmentation_quality_gate_metrics() -> list[BenchmarkMetric]:
    scan_dir = SAMPLE_CASE_DIR
    scans = [
        ("initial-upper.stl", "maxillary"),
        ("initial-lower.stl", "mandibular"),
    ]
    reviewable = 0
    production = 0
    metrics: list[BenchmarkMetric] = []
    for filename, arch in scans:
        _asset, vertices = read_mesh_geometry(scan_dir / filename)
        segments = load_local_segmenter().segment(vertices, arch=arch)  # type: ignore[arg-type]
        report = evaluate_segmentation_quality(segments, arch=arch)  # type: ignore[arg-type]
        reviewable += int(report.reviewable)
        production += int(report.production_candidate)
        metrics.extend(_arch_metrics(arch, report.mean_compactness, report.min_compactness))
    metrics.extend(_summary_metrics(reviewable, production))
    return metrics


def _arch_metrics(arch: str, mean_compactness: float, min_compactness: float) -> list[BenchmarkMetric]:
    return [
        _metric(
            "real_scan_segmentation_mean_compactness",
            mean_compactness,
            "segmentation-quality-gates",
            arch,
        ),
        _metric(
            "real_scan_segmentation_min_compactness",
            min_compactness,
            "segmentation-quality-gates",
            arch,
        ),
    ]


def _summary_metrics(reviewable: int, production: int) -> list[BenchmarkMetric]:
    return [
        _metric(
            "real_scan_reviewable_segmentation_arches",
            float(reviewable),
            "segmentation-quality-gates",
            SAMPLE_SPECIMEN_ID,
            notes="Bundled non-PHI real scans clearing reviewable segmentation gates.",
        ),
        _metric(
            "real_scan_production_candidate_arches",
            float(production),
            "segmentation-quality-gates",
            SAMPLE_SPECIMEN_ID,
            notes="Expected to remain 0 until a stronger backend clears production gates.",
        ),
    ]


def _metric(
    name: str,
    value: float,
    component: str,
    case_id: str,
    *,
    notes: str | None = None,
) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        value=round(value, 6),
        component=component,
        case_id=case_id,
        notes=notes,
    )
