from __future__ import annotations

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


def test_triangle_collision_rule_uses_full_surface_when_supplied() -> None:
    plan = _triangle_contact_plan(sample_a=(0.0, 0.0, 0.0), sample_b=(1.8, 1.0, 0.0))
    triangles_by_tooth = {
        "11": [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0))],
        "21": [((0.8, 0.0, 0.0), (1.8, 0.0, 0.0), (0.8, 1.0, 0.0))],
    }

    findings = evaluate_segmented_mesh_collisions(plan, triangles_by_tooth=triangles_by_tooth)

    assert len(findings) == 1
    assert "Minimum triangle-surface distance is 0.000 mm" in findings[0].message


def test_triangle_collision_rule_falls_back_to_samples_without_triangles() -> None:
    plan = _triangle_contact_plan(sample_a=(1.0, 0.5, 0.0), sample_b=(0.8, 0.5, 0.0))

    findings = evaluate_segmented_mesh_collisions(plan)

    assert len(findings) == 1
    assert "Minimum representative-surface distance is 0.200 mm" in findings[0].message


def _triangle_contact_plan(sample_a, sample_b) -> TreatmentPlan:
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
        id="triangle-contact",
        mesh_assets=[mesh_11, mesh_21],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="mesh-11",
                surface_sample_points=[sample_a],
            ),
            SegmentedToothMesh(
                tooth=ToothId(value="21"),
                mesh_asset_id="mesh-21",
                surface_sample_points=[sample_b],
            ),
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"))])],
    )
