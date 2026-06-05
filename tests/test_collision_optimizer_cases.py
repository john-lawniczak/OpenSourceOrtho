from __future__ import annotations

import pytest

from orthoplan.cases import CaseStore
from orthoplan.evaluation.rules.collisions import evaluate_segmented_mesh_collisions
from orthoplan.model import (
    BoundingBox,
    FixedTooth,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.model.clinical import MovementExclusion
from orthoplan.planning.optimizer import optimize_staging


def test_segmented_mesh_collision_rule_flags_transformed_bounds_overlap() -> None:
    mesh_11 = MeshAsset(
        id="mesh-11",
        format="stl-ascii",
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(1, 1, 1)),
    )
    mesh_21 = MeshAsset(
        id="mesh-21",
        format="stl-ascii",
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(2, 0, 0), max_xyz=(3, 1, 1)),
    )
    plan = TreatmentPlan(
        id="collision",
        mesh_assets=[mesh_11, mesh_21],
        tooth_meshes=[
            SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11"),
            SegmentedToothMesh(tooth=ToothId(value="21"), mesh_asset_id="mesh-21"),
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="21"), translate_x_mm=-1.5)])],
    )

    findings = evaluate_segmented_mesh_collisions(plan)

    assert len(findings) == 1
    assert "bounds overlap" in findings[0].title


def test_segmented_mesh_collision_rule_reports_one_finding_per_pair() -> None:
    mesh_11 = MeshAsset(
        id="mesh-11",
        format="stl-ascii",
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(1, 1, 1)),
    )
    mesh_21 = MeshAsset(
        id="mesh-21",
        format="stl-ascii",
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(2, 0, 0), max_xyz=(3, 1, 1)),
    )
    # Tooth 21 marches toward tooth 11; the overlap deepens every stage, so the
    # contact persists across stages 1 and 2 (deepest at stage 2).
    plan = TreatmentPlan(
        id="persistent-collision",
        mesh_assets=[mesh_11, mesh_21],
        tooth_meshes=[
            SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11"),
            SegmentedToothMesh(tooth=ToothId(value="21"), mesh_asset_id="mesh-21"),
        ],
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="21"), translate_x_mm=-0.6)]),
            Stage(index=1, deltas=[ToothDelta(tooth=ToothId(value="21"), translate_x_mm=-0.6)]),
            Stage(index=2, deltas=[ToothDelta(tooth=ToothId(value="21"), translate_x_mm=-0.6)]),
        ],
    )

    findings = evaluate_segmented_mesh_collisions(plan)

    assert len(findings) == 1
    assert "11 and 21" in findings[0].title
    assert "deepest at stage 2" in findings[0].message


def test_optimizer_splits_large_movement_by_configured_caps() -> None:
    plan = TreatmentPlan(
        id="optimize",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.6)])],
    )

    result = optimize_staging(plan)

    assert len(result.plan.stages) == 3
    assert [stage.deltas[0].translate_x_mm for stage in result.plan.stages] == pytest.approx([0.2, 0.2, 0.2])


def test_optimizer_respects_fixed_teeth_and_exclusions() -> None:
    plan = TreatmentPlan(
        id="optimize-controls",
        fixed_teeth=[FixedTooth(tooth=ToothId(value="11"))],
        movement_exclusions=[
            MovementExclusion(tooth=ToothId(value="21"), axes={"rotation"}),
        ],
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2),
                    ToothDelta(tooth=ToothId(value="21"), rotate_rotation_deg=2.0),
                ],
            )
        ],
    )

    result = optimize_staging(plan)

    assert result.plan.stages == []
    assert {issue.tooth for issue in result.issues} == {"11", "21"}


def test_case_store_versions_are_immutable_snapshots() -> None:
    store = CaseStore()
    plan = TreatmentPlan(
        id="case-plan",
        title="Case plan",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)])],
    )

    first = store.add_version("case-001", plan, note="initial")
    second = store.add_version(
        "case-001",
        plan.model_copy(update={"title": "Case plan revised"}),
        note="revision",
    )

    assert first.version_id == "v0001"
    assert second.version_id == "v0002"
    assert first.plan_hash != second.plan_hash
    assert store.cases["case-001"].versions[0].snapshot["title"] == "Case plan"
