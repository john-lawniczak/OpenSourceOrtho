"""Manifest-driven labelled real-scan segmentation benchmarks.

The repo intentionally does not ship patient-derived labelled scans or model
weights. This module defines the contract for externally supplied, PHI-free or
consented labelled cases so production-candidate segmentation can be gated on
real geometry without committing sensitive data.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.model.assets import ArchName
from orthoplan.segmentation.auto import SegmentationModel, load_local_segmenter
from orthoplan.segmentation.heuristic import _facets
from orthoplan.validation.benchmark_models import BenchmarkMetric
from orthoplan.validation.segmentation_truth import score_segmentation
from orthoplan.validation.synthetic_arch import _centroid_key

_MANIFEST_ENV = "OPENSOURCE_ORTHO_LABELLED_SEGMENTATION_CORPUS"


@dataclass(frozen=True)
class LabelledRealArch:
    """Minimal truth object accepted by ``score_segmentation``."""

    vertices: list[tuple[float, float, float]]
    tooth_values: tuple[str, ...]
    expected_count: int
    truth_by_centroid: dict[tuple[int, int, int], str]
    arc_center: dict[str, float]


def labelled_real_scan_metrics(
    *,
    manifest_path: str | Path | None = None,
    segmenter: SegmentationModel | None = None,
) -> list[BenchmarkMetric]:
    """Return metrics for external labelled real-scan cases, or skipped metrics."""

    path = Path(manifest_path or os.environ.get(_MANIFEST_ENV, ""))
    if not str(path):
        return _skipped_metrics("No labelled real-scan corpus manifest configured.")
    if not path.is_file():
        return _skipped_metrics(f"Labelled real-scan corpus manifest not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return _skipped_metrics("Labelled real-scan corpus manifest has no cases list.")

    active = segmenter or load_local_segmenter()
    metrics: list[BenchmarkMetric] = [
        _metric(
            "labelled_real_scan_cases",
            float(len(cases)),
            "labelled-real-scan-corpus",
            "manifest",
        ),
    ]
    license_clear = 0
    scored = 0
    for raw in cases:
        if not isinstance(raw, dict):
            continue
        case_metrics, case_license_clear, case_scored = _score_case(raw, root=path.parent, segmenter=active)
        metrics.extend(case_metrics)
        license_clear += int(case_license_clear)
        scored += int(case_scored)
    metrics.extend(_manifest_summary_metrics(license_clear, scored))
    return metrics


def _score_case(
    raw: dict, *, root: Path, segmenter: SegmentationModel
) -> tuple[list[BenchmarkMetric], bool, bool]:
    case_id = str(raw.get("case_id", "unnamed-case"))
    if not _provenance_ok(raw):
        return [
            _metric(
                "labelled_real_scan_case_license_clear",
                0.0,
                "labelled-real-scan-corpus",
                case_id,
                notes=(
                    "Case skipped: requires phi_removed, consent_acknowledged, "
                    "and commercial_use_allowed."
                ),
            )
        ], False, False

    arch = _arch(raw.get("arch"))
    labelled = _load_labelled_arch(
        _resolve(root, raw.get("scan_path")),
        _resolve(root, raw.get("labels_path")),
    )
    score = score_segmentation(segmenter.segment(labelled.vertices, arch=arch), labelled)
    return [
        _metric("labelled_real_scan_case_license_clear", 1.0, "labelled-real-scan-corpus", case_id),
        _metric(
            "labelled_real_scan_triangle_label_accuracy",
            score.triangle_label_accuracy,
            "labelled-real-scan-corpus",
            case_id,
        ),
        _metric(
            "labelled_real_scan_region_purity",
            score.region_purity,
            "labelled-real-scan-corpus",
            case_id,
        ),
    ], True, True


def _manifest_summary_metrics(license_clear: int, scored: int) -> list[BenchmarkMetric]:
    return [
        _metric(
            "license_clear_labelled_real_scan_cases",
            float(license_clear),
            "labelled-real-scan-corpus",
            "manifest",
        ),
        _metric(
            "scored_labelled_real_scan_cases",
            float(scored),
            "labelled-real-scan-corpus",
            "manifest",
        ),
    ]


def _load_labelled_arch(scan_path: Path, labels_path: Path) -> LabelledRealArch:
    _asset, vertices = read_stl_geometry(scan_path)
    facets = _facets(vertices)
    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = payload.get("triangle_labels")
    if not isinstance(labels, list) or len(labels) != len(facets):
        raise ValueError("triangle_labels must contain one FDI label per STL triangle")
    truth = {}
    for tri, label in zip(facets, labels):
        centroid = (
            (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
            (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
            (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
        )
        truth[_centroid_key(centroid)] = str(label)
    tooth_values = tuple(sorted(set(truth.values())))
    return LabelledRealArch(
        vertices=vertices,
        tooth_values=tooth_values,
        expected_count=len(tooth_values),
        truth_by_centroid=truth,
        arc_center={tooth: 0.0 for tooth in tooth_values},
    )


def _provenance_ok(raw: dict) -> bool:
    return all(bool(raw.get(key)) for key in (
        "phi_removed",
        "consent_acknowledged",
        "commercial_use_allowed",
    ))


def _resolve(root: Path, raw: object) -> Path:
    path = Path(str(raw))
    return path if path.is_absolute() else root / path


def _arch(raw: object) -> ArchName:
    if raw in {"maxillary", "mandibular"}:
        return raw  # type: ignore[return-value]
    raise ValueError("labelled real-scan case arch must be maxillary or mandibular")


def _skipped_metrics(reason: str) -> list[BenchmarkMetric]:
    return [
        _metric("labelled_real_scan_cases", 0.0, "labelled-real-scan-corpus", "manifest", notes=reason),
        _metric("license_clear_labelled_real_scan_cases", 0.0, "labelled-real-scan-corpus", "manifest", notes=reason),
        _metric("scored_labelled_real_scan_cases", 0.0, "labelled-real-scan-corpus", "manifest", notes=reason),
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
