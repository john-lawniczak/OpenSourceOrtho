from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.model.dataset import DatasetManifest, read_manifest
from orthoplan.validation.benchmark_models import BenchmarkMetric


class OutcomeErrorMetric(BaseModel):
    name: str
    specimen_id: str
    role: str
    arch: str | None = None
    value_mm: float | None = None
    status: str
    notes: str


class RefinementPredictionReport(BaseModel):
    specimen_id: str
    planned_refinements: int | None
    observed_refinement_scans: int
    planned_observed: int
    unplanned_observed: int
    missing_or_unknown: int
    status: str


class LongitudinalOutcomeReport(BaseModel):
    specimen_id: str
    target_setup_errors: list[OutcomeErrorMetric] = Field(default_factory=list)
    tracking_errors: list[OutcomeErrorMetric] = Field(default_factory=list)
    refinement_prediction: RefinementPredictionReport
    caveat: str = (
        "Outcome reports use consented non-PHI manifest metadata and simple scan "
        "bounds proxies until reviewed comparable geometry is available. Sparse "
        "community data must not be overstated as clinical accuracy."
    )


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


def longitudinal_outcome_reports(root: str | Path | None = None) -> list[LongitudinalOutcomeReport]:
    """Numeric outcome-error reports for consented longitudinal bundles.

    The current public contribution manifest deliberately stores metadata, not
    patient mesh bytes. These reports therefore use bounds-centroid deltas as a
    deterministic proxy and mark missing timing/geometry explicitly.
    """

    manifests = _load_manifests(Path(root) if root else _default_manifest_root())
    return [_outcome_report(manifest) for manifest in manifests]


def _outcome_report(manifest: DatasetManifest) -> LongitudinalOutcomeReport:
    return LongitudinalOutcomeReport(
        specimen_id=manifest.specimen_id,
        target_setup_errors=_target_setup_errors(manifest),
        tracking_errors=_tracking_errors(manifest),
        refinement_prediction=_refinement_prediction_report(manifest),
    )


def _target_setup_errors(manifest: DatasetManifest) -> list[OutcomeErrorMetric]:
    metrics: list[OutcomeErrorMetric] = []
    for arch in ("maxillary", "mandibular"):
        initial = _scan_for(manifest, "initial", arch)
        outcome = _scan_for(manifest, "final", arch) or _scan_for(manifest, "refinement", arch)
        metrics.append(
            _bounds_delta_metric(
                manifest,
                "target_setup_bounds_centroid_error_mm",
                "target-setup",
                arch,
                initial,
                outcome,
                "initial scan compared with final/refinement scan bounds",
            )
        )
    return metrics


def _tracking_errors(manifest: DatasetManifest) -> list[OutcomeErrorMetric]:
    progress_scans = [scan for scan in manifest.scans if scan.role == "progress"]
    if not progress_scans:
        return [
            OutcomeErrorMetric(
                name="tracking_bounds_centroid_error_mm",
                specimen_id=manifest.specimen_id,
                role="tracking",
                status="missing-progress-scans",
                notes="No progress scan with known stage timing is present.",
            )
        ]
    metrics: list[OutcomeErrorMetric] = []
    for progress in progress_scans:
        baseline = _scan_for(manifest, "initial", progress.arch)
        status = "ok" if progress.sequence_index is not None else "missing-stage-timing"
        metric = _bounds_delta_metric(
            manifest,
            "tracking_bounds_centroid_error_mm",
            "tracking",
            progress.arch,
            baseline,
            progress,
            "initial scan compared with progress scan bounds",
        )
        if status != "ok":
            metric.status = status
            metric.value_mm = None
            metric.notes = "Progress scan exists, but stage timing is unknown."
        metrics.append(metric)
    return metrics


def _refinement_prediction_report(manifest: DatasetManifest) -> RefinementPredictionReport:
    planned = manifest.plan_summary.refinement_count if manifest.plan_summary else None
    observed = sum(1 for scan in manifest.scans if scan.role == "refinement")
    if planned is None:
        return RefinementPredictionReport(
            specimen_id=manifest.specimen_id,
            planned_refinements=None,
            observed_refinement_scans=observed,
            planned_observed=0,
            unplanned_observed=observed,
            missing_or_unknown=1,
            status="missing-plan-summary",
        )
    planned_observed = min(planned, observed)
    unplanned = max(0, observed - planned)
    missing = max(0, planned - observed)
    return RefinementPredictionReport(
        specimen_id=manifest.specimen_id,
        planned_refinements=planned,
        observed_refinement_scans=observed,
        planned_observed=planned_observed,
        unplanned_observed=unplanned,
        missing_or_unknown=missing,
        status="ok" if unplanned == 0 and missing == 0 else "incomplete-or-unplanned",
    )


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


def _scan_for(manifest: DatasetManifest, role: str, arch: str | None):
    scans = [
        scan for scan in manifest.scans
        if scan.role == role and scan.arch == arch and scan.bounds is not None
    ]
    return sorted(scans, key=lambda scan: scan.sequence_index or 0)[-1] if scans else None


def _bounds_delta_metric(
    manifest: DatasetManifest,
    name: str,
    role: str,
    arch: str | None,
    before,
    after,
    notes: str,
) -> OutcomeErrorMetric:
    if before is None or after is None:
        return OutcomeErrorMetric(
            name=name,
            specimen_id=manifest.specimen_id,
            role=role,
            arch=arch,
            status="missing-comparable-scan-bounds",
            notes="Comparable consented scan bounds are not present for this arch.",
        )
    return OutcomeErrorMetric(
        name=name,
        specimen_id=manifest.specimen_id,
        role=role,
        arch=arch,
        value_mm=round(_centroid_distance(before.bounds, after.bounds), 6),
        status="ok",
        notes=notes,
    )


def _centroid_distance(a, b) -> float:
    ac = _bounds_center(a)
    bc = _bounds_center(b)
    return sum((ac[i] - bc[i]) ** 2 for i in range(3)) ** 0.5


def _bounds_center(bounds) -> tuple[float, float, float]:
    return tuple(
        (bounds.min_xyz[i] + bounds.max_xyz[i]) / 2.0
        for i in range(3)
    )  # type: ignore[return-value]


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
