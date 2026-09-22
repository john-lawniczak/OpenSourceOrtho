from __future__ import annotations

from pathlib import Path

from orthoplan.model.dataset import (
    BoundingBox,
    ContributedScan,
    DatasetManifest,
    PlanSummary,
    write_manifest,
)
from orthoplan.validation.longitudinal_benchmark import (
    longitudinal_case_metrics,
    longitudinal_outcome_reports,
)


def _scan(filename: str, role: str, arch: str, *, sequence_index: int | None = None, offset: float = 0) -> ContributedScan:
    return ContributedScan(
        filename=filename,
        role=role,  # type: ignore[arg-type]
        sequence_index=sequence_index,
        sha256="a" * 64,
        units="mm",
        arch=arch,  # type: ignore[arg-type]
        vertex_count=3,
        face_count=1,
        bounds=BoundingBox(
            min_xyz=(offset, 0, 0),
            max_xyz=(offset + 2, 2, 2),
        ),
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


def test_longitudinal_outcome_reports_compute_bounds_proxy_errors(tmp_path: Path) -> None:
    manifest = DatasetManifest(
        scans=[
            _scan("initial-upper.stl", "initial", "maxillary", offset=0),
            _scan("initial-lower.stl", "initial", "mandibular", offset=0),
            _scan("final-upper.stl", "final", "maxillary", offset=0.5),
            _scan("final-lower.stl", "final", "mandibular", offset=0.25),
            _scan("progress-01-upper.stl", "progress", "maxillary", sequence_index=1, offset=0.2),
            _scan("refinement-01-upper.stl", "refinement", "maxillary", sequence_index=1, offset=0.6),
        ],
        plan_summary=PlanSummary(stage_count=12, refinement_count=1),
        consent_acknowledged=True,
        phi_removed=True,
    )
    write_manifest(manifest, tmp_path / "spec-ready" / "manifest.json")

    report = longitudinal_outcome_reports(tmp_path)[0]

    assert report.target_setup_errors[0].status == "ok"
    assert report.target_setup_errors[0].value_mm == 0.5
    assert report.tracking_errors[0].status == "ok"
    assert report.tracking_errors[0].value_mm == 0.2
    assert report.refinement_prediction.status == "ok"
    assert report.refinement_prediction.planned_observed == 1


def test_longitudinal_outcome_reports_separate_unplanned_and_unknown(tmp_path: Path) -> None:
    manifest = DatasetManifest(
        scans=[
            _scan("initial-upper.stl", "initial", "maxillary"),
            _scan("progress-upper.stl", "progress", "maxillary", offset=0.1),
            _scan("refinement-01-upper.stl", "refinement", "maxillary", sequence_index=1, offset=0.4),
        ],
        consent_acknowledged=True,
        phi_removed=True,
    )
    write_manifest(manifest, tmp_path / "spec-unknown" / "manifest.json")

    report = longitudinal_outcome_reports(tmp_path)[0]

    assert report.tracking_errors[0].status == "missing-stage-timing"
    assert report.tracking_errors[0].value_mm is None
    assert report.refinement_prediction.status == "missing-plan-summary"
    assert report.refinement_prediction.unplanned_observed == 1
    assert report.refinement_prediction.missing_or_unknown == 1
