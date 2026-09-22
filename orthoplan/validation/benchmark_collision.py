from __future__ import annotations

from orthoplan.evaluation.rules.contact_geometry import staged_contact_candidates
from orthoplan.model import (
    BoundingBox,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.validation.benchmark_models import BenchmarkMetric


def triangle_collision_metrics() -> list[BenchmarkMetric]:
    plan = _triangle_collision_plan()
    bounds = {
        asset.id.replace("mesh-", ""): asset.bounds
        for asset in plan.mesh_assets
        if asset.bounds is not None
    }
    sampled = staged_contact_candidates(plan, bounds)
    triangle = staged_contact_candidates(
        plan,
        bounds,
        triangles_by_tooth={
            "11": [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0))],
            "21": [((0.8, 0.0, 0.0), (1.8, 0.0, 0.0), (0.8, 1.0, 0.0))],
        },
    )
    sampled_distance = next(iter(sampled.values())).sample_distance_mm or 0.0
    triangle_distance = next(iter(triangle.values())).triangle_distance_mm or 0.0
    return [
        _metric("collision_sample_distance", sampled_distance),
        _metric("collision_triangle_distance", triangle_distance),
        _metric("collision_triangle_delta_vs_sample", triangle_distance - sampled_distance),
    ]


def _metric(name: str, value: float) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        value=round(value, 6),
        component="collision-ipr",
        case_id="triangle-contact-pair",
        unit="mm",
    )


def _triangle_collision_plan() -> TreatmentPlan:
    mesh_11 = MeshAsset(
        id="mesh-11",
        format="stl-ascii",
        vertex_count=3,
        face_count=1,
        bounds=BoundingBox(min_xyz=(0, 0, -0.01), max_xyz=(1, 1, 0.01)),
    )
    mesh_21 = MeshAsset(
        id="mesh-21",
        format="stl-ascii",
        vertex_count=3,
        face_count=1,
        bounds=BoundingBox(min_xyz=(0.8, 0, -0.01), max_xyz=(1.8, 1, 0.01)),
    )
    return TreatmentPlan(
        id="triangle-contact-pair",
        mesh_assets=[mesh_11, mesh_21],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="mesh-11",
                surface_sample_points=[(0.0, 0.0, 0.0)],
            ),
            SegmentedToothMesh(
                tooth=ToothId(value="21"),
                mesh_asset_id="mesh-21",
                surface_sample_points=[(1.8, 1.0, 0.0)],
            ),
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"))])],
    )
