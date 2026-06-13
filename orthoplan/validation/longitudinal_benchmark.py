from __future__ import annotations

from pathlib import Path

from orthoplan.model.dataset import DatasetManifest, read_manifest
from orthoplan.validation.benchmark_models import BenchmarkMetric


def longitudinal_case_metrics(root: str | Path | None = None) -> list[BenchmarkMetric]:
    """Report readiness metrics for privacy-safe longitudinal contribution bundles."""

    manifests = _load_manifests(Path(root) if root else _default_manifest_root())
    if not manifests:
        return [_metric("longitudinal_manifest_cases", 0.0, "no-manifests")]

    target_ready = sum(1 for manifest in manifests if _has_initial_pair(manifest))
    tracking_ready = sum(1 for manifest in manifests if _has_initial_pair(manifest) and _has_final_pair(manifest))
    refinement_ready = sum(
        1
        for manifest in manifests
        if _has_progress_or_refinement(manifest) or _planned_refinement_count(manifest) > 0
    )
    plan_context = sum(1 for manifest in manifests if manifest.plan_summary is not None)
    return [
        _metric("longitudinal_manifest_cases", float(len(manifests)), "case-bundles"),
        _metric("target_setup_ready_cases", float(target_ready), "initial-scan-pairs"),
        _metric("tracking_error_ready_cases", float(tracking_ready), "initial-final-pairs"),
        _metric("refinement_prediction_ready_cases", float(refinement_ready), "refinement-signals"),
        _metric("plan_context_ready_cases", float(plan_context), "plan-summary-sidecars"),
        _metric(
            "tracking_error_readiness_ratio",
            tracking_ready / len(manifests),
            "initial-final-pairs",
        ),
        _metric(
            "refinement_prediction_readiness_ratio",
            refinement_ready / len(manifests),
            "refinement-signals",
        ),
    ]


def _load_manifests(root: Path) -> list[DatasetManifest]:
    if root.is_file():
        paths = [root]
    elif root.exists():
        paths = sorted(root.rglob("manifest.json"))
    else:
        paths = []
    manifests: list[DatasetManifest] = []
    for path in paths:
        try:
            manifest = read_manifest(path)
        except (OSError, ValueError):
            continue
        if manifest.phi_removed and manifest.consent_acknowledged:
            manifests.append(manifest)
    return manifests


def _has_initial_pair(manifest: DatasetManifest) -> bool:
    return _has_arch_pair(manifest, "initial")


def _has_final_pair(manifest: DatasetManifest) -> bool:
    return _has_arch_pair(manifest, "final")


def _has_arch_pair(manifest: DatasetManifest, role: str) -> bool:
    arches = {scan.arch for scan in manifest.scans if scan.role == role}
    return {"maxillary", "mandibular"} <= arches


def _has_progress_or_refinement(manifest: DatasetManifest) -> bool:
    return any(scan.role in {"progress", "refinement"} for scan in manifest.scans)


def _planned_refinement_count(manifest: DatasetManifest) -> int:
    if manifest.plan_summary is None or manifest.plan_summary.refinement_count is None:
        return 0
    return manifest.plan_summary.refinement_count


def _metric(name: str, value: float, case_id: str) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        value=round(value, 6),
        component="longitudinal-data",
        case_id=case_id,
        notes=(
            "Readiness metric for target setup, tracking error, and refinement "
            "prediction benchmarks from consented non-PHI longitudinal bundles."
        ),
    )


def _default_manifest_root() -> Path:
    return Path(__file__).resolve().parents[2]
