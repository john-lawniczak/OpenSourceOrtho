from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.aligner_shell import build_aligner_shell
from orthoplan.evaluation.rules.collisions import evaluate_segmented_mesh_collisions
from orthoplan.model import (
    BoundingBox,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.validation.segmentation_truth import full_arch_truth, score_segmentation
from orthoplan.validation.synthetic_arch import build_synthetic_arch, realistic_widths
from orthoplan.viz.progress import build_stage_progress_frames


class BenchmarkMetric(BaseModel):
    name: str
    value: float
    unit: str = ""
    component: str
    case_id: str
    notes: str | None = None


class BenchmarkReport(BaseModel):
    benchmark_id: str = "synthetic-validation-v1"
    caveat: str = (
        "Synthetic benchmark metrics are tracked numbers, not pass/fail clinical "
        "clearance. Reviewed open-dataset cases can be added beside these fixtures."
    )
    metrics: list[BenchmarkMetric] = Field(default_factory=list)

    def by_component(self) -> dict[str, list[BenchmarkMetric]]:
        grouped: dict[str, list[BenchmarkMetric]] = {}
        for metric in self.metrics:
            grouped.setdefault(metric.component, []).append(metric)
        return grouped


def run_validation_benchmarks() -> BenchmarkReport:
    metrics: list[BenchmarkMetric] = []
    metrics.extend(_segmentation_metrics())
    metrics.extend(_movement_metrics())
    metrics.extend(_collision_metrics())
    metrics.extend(_shell_metrics())
    return BenchmarkReport(metrics=metrics)


def _segmentation_metrics() -> list[BenchmarkMetric]:
    arch = build_synthetic_arch(
        full_arch_truth("maxillary"),
        sector_weights=realistic_widths(full_arch_truth("maxillary")),
        occlusal_flat=0.35,
        noise=0.02,
    )
    segments = load_local_segmenter().segment(arch.vertices, arch="maxillary")
    score = score_segmentation(segments, arch)
    accuracy = score.triangle_label_accuracy
    dice = 2 * accuracy / (1 + accuracy) if accuracy else 0.0
    iou = accuracy / (2 - accuracy) if accuracy else 0.0
    return [
        _metric("segmentation_dice", dice, "segmentation", "synthetic-arch"),
        _metric("segmentation_iou", iou, "segmentation", "synthetic-arch"),
        _metric("region_purity", score.region_purity, "segmentation", "synthetic-arch"),
    ]


def _movement_metrics() -> list[BenchmarkMetric]:
    plan = TreatmentPlan(
        id="benchmark-movement",
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)]),
            Stage(index=1, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_y_mm=0.3)]),
        ],
    )
    pose = build_stage_progress_frames(plan)[1].poses[0]
    error = abs(pose.translate_x_mm - 0.2) + abs(pose.translate_y_mm - 0.3)
    return [_metric("movement_translation_error", error, "movement", plan.id, unit="mm")]


def _collision_metrics() -> list[BenchmarkMetric]:
    cases = [(_collision_plan(True), True), (_collision_plan(False), False)]
    tp = fp = fn = 0
    for plan, expected in cases:
        observed = bool(evaluate_segmented_mesh_collisions(plan))
        tp += int(observed and expected)
        fp += int(observed and not expected)
        fn += int((not observed) and expected)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return [
        _metric("collision_ipr_precision", precision, "collision-ipr", "sample-contact-pair"),
        _metric("collision_ipr_recall", recall, "collision-ipr", "sample-contact-pair"),
    ]


def _shell_metrics() -> list[BenchmarkMetric]:
    quad = [
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)),
        ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
    ]
    requested = 0.6
    shell = build_aligner_shell(quad, thickness_mm=requested)
    error = abs(shell.stats.measured_thickness_mm - requested)
    return [_metric("shell_thickness_error", error, "shell-thickness", "flat-quad", unit="mm")]


def _collision_plan(overlap: bool) -> TreatmentPlan:
    bounds_21 = (0.8, 1.8) if overlap else (1.3, 2.3)
    mesh_11 = MeshAsset(
        id="mesh-11", format="stl-ascii", vertex_count=8, face_count=12,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(1, 1, 1)),
    )
    mesh_21 = MeshAsset(
        id="mesh-21", format="stl-ascii", vertex_count=8, face_count=12,
        bounds=BoundingBox(min_xyz=(bounds_21[0], 0, 0), max_xyz=(bounds_21[1], 1, 1)),
    )
    return TreatmentPlan(
        id="benchmark-collision-overlap" if overlap else "benchmark-collision-clear",
        mesh_assets=[mesh_11, mesh_21],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="mesh-11",
                surface_sample_points=[(1.0, 0.5, 0.5)],
            ),
            SegmentedToothMesh(
                tooth=ToothId(value="21"),
                mesh_asset_id="mesh-21",
                surface_sample_points=[(bounds_21[0], 0.5, 0.5)],
            ),
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"))])],
    )


def _metric(
    name: str, value: float, component: str, case_id: str, *, unit: str = ""
) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        value=round(value, 6),
        unit=unit,
        component=component,
        case_id=case_id,
    )
