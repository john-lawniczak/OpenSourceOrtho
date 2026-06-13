from __future__ import annotations

from pathlib import Path

from orthoplan.model.dataset import (
    ContributedScan,
    DatasetManifest,
    PlanSummary,
    write_manifest,
)
from orthoplan.validation.longitudinal_benchmark import longitudinal_case_metrics


def _scan(filename: str, role: str, arch: str) -> ContributedScan:
    return ContributedScan(
        filename=filename,
        role=role,  # type: ignore[arg-type]
        sha256="a" * 64,
        units="mm",
        arch=arch,  # type: ignore[arg-type]
        vertex_count=3,
        face_count=1,
    )


def _metric_value(root: Path, name: str) -> float:
    metric = next(item for item in longitudinal_case_metrics(root) if item.name == name)
    return metric.value


def test_longitudinal_metrics_score_ready_case_bundle(tmp_path: Path) -> None:
    manifest = DatasetManifest(
        scans=[
            _scan("initial-upper.stl", "initial", "maxillary"),
            _scan("initial-lower.stl", "initial", "mandibular"),
            _scan("final-upper.stl", "final", "maxillary"),
            _scan("final-lower.stl", "final", "mandibular"),
            _scan("progress-01-upper.stl", "progress", "maxillary"),
        ],
        plan_summary=PlanSummary(stage_count=12, refinement_count=1),
        consent_acknowledged=True,
        phi_removed=True,
    )
    write_manifest(manifest, tmp_path / "spec-ready" / "manifest.json")

    assert _metric_value(tmp_path, "longitudinal_manifest_cases") == 1.0
    assert _metric_value(tmp_path, "target_setup_ready_cases") == 1.0
    assert _metric_value(tmp_path, "tracking_error_ready_cases") == 1.0
    assert _metric_value(tmp_path, "refinement_prediction_ready_cases") == 1.0
    assert _metric_value(tmp_path, "plan_context_ready_cases") == 1.0
    assert _metric_value(tmp_path, "tracking_error_readiness_ratio") == 1.0


def test_longitudinal_metrics_skip_unconsented_manifest(tmp_path: Path) -> None:
    manifest = DatasetManifest(
        scans=[_scan("initial-upper.stl", "initial", "maxillary")],
        consent_acknowledged=False,
        phi_removed=True,
    )
    write_manifest(manifest, tmp_path / "spec-skip" / "manifest.json")

    assert longitudinal_case_metrics(tmp_path)[0].name == "longitudinal_manifest_cases"
    assert longitudinal_case_metrics(tmp_path)[0].value == 0.0
