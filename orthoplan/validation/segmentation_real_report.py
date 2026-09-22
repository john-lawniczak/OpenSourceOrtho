"""Pass/fail report for labelled real-scan segmentation benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.model.assets import ArchName
from orthoplan.segmentation.auto import HybridArchSegmenter, SegmentationModel, load_local_segmenter
from orthoplan.validation.segmentation_real_corpus import (
    _arch,
    _load_labelled_arch,
    _provenance_ok,
    _resolve,
)
from orthoplan.validation.segmentation_truth import score_segmentation


class LabelledSegmentationCaseResult(BaseModel):
    case_id: str
    arch: ArchName | None = None
    license_clear: bool = False
    skipped_reason: str | None = None
    expected_tooth_count: int = 0
    observed_tooth_count: int = 0
    triangle_label_accuracy: float = 0.0
    region_purity: float = 0.0
    fallback_triangle_label_accuracy: float = 0.0
    fallback_region_purity: float = 0.0
    review_burden_delta_vs_fallback: float = 0.0
    passed: bool = False
    failures: list[str] = Field(default_factory=list)


class LabelledSegmentationBenchmarkReport(BaseModel):
    manifest_path: str
    candidate_backend: str
    fallback_backend: str = "hybrid-arch-graph-cut"
    min_cases: int = 1
    min_triangle_label_accuracy: float = 0.95
    min_region_purity: float = 0.95
    cases: list[LabelledSegmentationCaseResult] = Field(default_factory=list)
    caveat: str = (
        "Labelled real-scan benchmarks measure segmentation against supplied "
        "ground truth. They are not clinical clearance and require PHI-safe, "
        "consented, license-clear source data."
    )

    @property
    def scored_case_count(self) -> int:
        return sum(1 for case in self.cases if case.license_clear and case.skipped_reason is None)

    @property
    def passed(self) -> bool:
        scored = [case for case in self.cases if case.license_clear and case.skipped_reason is None]
        return len(scored) >= self.min_cases and all(case.passed for case in scored)


def labelled_real_scan_report(
    *,
    manifest_path: str | Path,
    candidate_segmenter: SegmentationModel | None = None,
    fallback_segmenter: SegmentationModel | None = None,
    min_triangle_label_accuracy: float = 0.95,
    min_region_purity: float = 0.95,
    min_cases: int = 1,
) -> LabelledSegmentationBenchmarkReport:
    """Score active/local segmentation against labelled real-scan truth."""

    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("Labelled real-scan corpus manifest has no cases list.")

    candidate = candidate_segmenter or load_local_segmenter()
    fallback = fallback_segmenter or HybridArchSegmenter()
    results = [
        _score_case_for_report(
            raw,
            root=path.parent,
            candidate=candidate,
            fallback=fallback,
            min_triangle_label_accuracy=min_triangle_label_accuracy,
            min_region_purity=min_region_purity,
        )
        for raw in cases
        if isinstance(raw, dict)
    ]
    return LabelledSegmentationBenchmarkReport(
        manifest_path=str(path),
        candidate_backend=getattr(candidate, "name", type(candidate).__name__),
        fallback_backend=getattr(fallback, "name", type(fallback).__name__),
        min_cases=min_cases,
        min_triangle_label_accuracy=min_triangle_label_accuracy,
        min_region_purity=min_region_purity,
        cases=results,
    )


def _score_case_for_report(
    raw: dict,
    *,
    root: Path,
    candidate: SegmentationModel,
    fallback: SegmentationModel,
    min_triangle_label_accuracy: float,
    min_region_purity: float,
) -> LabelledSegmentationCaseResult:
    case_id = str(raw.get("case_id", "unnamed-case"))
    if not _provenance_ok(raw):
        return LabelledSegmentationCaseResult(
            case_id=case_id,
            skipped_reason="requires phi_removed, consent_acknowledged, and commercial_use_allowed",
        )

    arch = _arch(raw.get("arch"))
    labelled = _load_labelled_arch(
        _resolve(root, raw.get("scan_path")),
        _resolve(root, raw.get("labels_path")),
    )
    candidate_score = score_segmentation(candidate.segment(labelled.vertices, arch=arch), labelled)
    fallback_score = score_segmentation(fallback.segment(labelled.vertices, arch=arch), labelled)
    failures = _gate_failures(
        candidate_score.triangle_label_accuracy,
        candidate_score.region_purity,
        min_triangle_label_accuracy=min_triangle_label_accuracy,
        min_region_purity=min_region_purity,
    )
    delta = _review_burden(candidate_score) - _review_burden(fallback_score)
    return LabelledSegmentationCaseResult(
        case_id=case_id,
        arch=arch,
        license_clear=True,
        expected_tooth_count=candidate_score.expected_count,
        observed_tooth_count=candidate_score.observed_count,
        triangle_label_accuracy=candidate_score.triangle_label_accuracy,
        region_purity=candidate_score.region_purity,
        fallback_triangle_label_accuracy=fallback_score.triangle_label_accuracy,
        fallback_region_purity=fallback_score.region_purity,
        review_burden_delta_vs_fallback=round(delta, 6),
        passed=not failures,
        failures=failures,
    )


def _gate_failures(
    triangle_label_accuracy: float,
    region_purity: float,
    *,
    min_triangle_label_accuracy: float,
    min_region_purity: float,
) -> list[str]:
    failures = []
    if triangle_label_accuracy < min_triangle_label_accuracy:
        failures.append("triangle-label-accuracy-below-floor")
    if region_purity < min_region_purity:
        failures.append("region-purity-below-floor")
    return failures


def _review_burden(score) -> float:
    count_error = abs(score.observed_count - score.expected_count)
    return count_error + (1.0 - score.triangle_label_accuracy) + (1.0 - score.region_purity)
