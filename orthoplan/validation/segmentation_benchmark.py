"""Learned-vs-heuristic segmentation maturity benchmarks."""

from __future__ import annotations

from orthoplan.segmentation.auto import HeuristicArchSegmenter, SegmentationModel
from orthoplan.segmentation.learned import SegmenterUnavailable, load_learned_segmenter
from orthoplan.validation.benchmark_models import BenchmarkMetric
from orthoplan.validation.segmentation_truth import (
    SyntheticArch,
    build_synthetic_arch,
    full_arch_truth,
    realistic_widths,
    score_segmentation,
)


def segmentation_maturity_metrics(
    learned_segmenter: SegmentationModel | None = None,
) -> list[BenchmarkMetric]:
    """Score heuristic fallback and optional learned backend on hard arch cases."""

    cases = _segmentation_cases()
    heuristic = HeuristicArchSegmenter()
    metrics = _score_backend("heuristic", heuristic, cases)

    learned = learned_segmenter if learned_segmenter is not None else _load_optional_learned()
    if learned is None:
        metrics.append(
            _metric(
                "learned_backend_available",
                0.0,
                "segmentation-learned",
                "phase-13-16-corpus",
                notes="Optional learned ONNX backend unavailable; heuristic fallback is active.",
            )
        )
        return metrics

    metrics.append(
        _metric("learned_backend_available", 1.0, "segmentation-learned", "phase-13-16-corpus")
    )
    learned_metrics = _score_backend("learned", learned, cases)
    metrics.extend(learned_metrics)
    metrics.extend(_delta_metrics(metrics, cases))
    return metrics


def _segmentation_cases() -> dict[str, SyntheticArch]:
    teeth = full_arch_truth("maxillary")
    return {
        "phase-13-clean-full-arch": build_synthetic_arch(teeth),
        "phase-13-realistic-crowded-arch": build_synthetic_arch(
            teeth,
            sector_weights=realistic_widths(teeth),
            occlusal_flat=0.65,
            noise=0.12,
        ),
        "phase-16-contacting-crowns": build_synthetic_arch(
            teeth,
            sector_weights=realistic_widths(teeth),
            occlusal_flat=0.82,
            noise=0.18,
        ),
    }


def _load_optional_learned() -> SegmentationModel | None:
    try:
        return load_learned_segmenter()
    except SegmenterUnavailable:
        return None
    except Exception:  # noqa: BLE001 - benchmark must not break fallback builds
        return None


def _score_backend(
    prefix: str, segmenter: SegmentationModel, cases: dict[str, SyntheticArch]
) -> list[BenchmarkMetric]:
    metrics: list[BenchmarkMetric] = []
    for case_id, arch in cases.items():
        score = score_segmentation(segmenter.segment(arch.vertices, arch="maxillary"), arch)
        accuracy = score.triangle_label_accuracy
        dice = 2 * accuracy / (1 + accuracy) if accuracy else 0.0
        iou = accuracy / (2 - accuracy) if accuracy else 0.0
        burden = (
            abs(score.observed_count - score.expected_count)
            + (1.0 - score.region_purity)
            + (1.0 - score.triangle_label_accuracy)
        )
        metrics.extend(
            [
                _metric(f"{prefix}_segmentation_dice", dice, "segmentation-learned", case_id),
                _metric(f"{prefix}_segmentation_iou", iou, "segmentation-learned", case_id),
                _metric(
                    f"{prefix}_manual_review_burden_proxy",
                    burden,
                    "segmentation-learned",
                    case_id,
                    notes="Lower is better: count error plus impurity plus label error.",
                ),
            ]
        )
    return metrics


def _delta_metrics(
    metrics: list[BenchmarkMetric], cases: dict[str, SyntheticArch]
) -> list[BenchmarkMetric]:
    by_key = {(m.name, m.case_id): m.value for m in metrics}
    out: list[BenchmarkMetric] = []
    for case_id in cases:
        learned = by_key.get(("learned_manual_review_burden_proxy", case_id))
        heuristic = by_key.get(("heuristic_manual_review_burden_proxy", case_id))
        if learned is None or heuristic is None:
            continue
        out.append(
            _metric(
                "learned_review_burden_delta_vs_heuristic",
                learned - heuristic,
                "segmentation-learned",
                case_id,
                notes="Negative means the learned backend reduced expected manual cleanup.",
            )
        )
    return out


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
