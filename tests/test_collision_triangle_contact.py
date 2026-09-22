from __future__ import annotations

from pathlib import Path

from orthoplan.api import evaluate_plan_payload
from orthoplan.evaluation.rules.collisions import evaluate_segmented_mesh_collisions
from orthoplan.mesh_workspace import register_stl_mesh
from orthoplan.model import (
    BoundingBox,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)

_STL_11 = """solid tooth11
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 1 0
    endloop
  endfacet
endsolid tooth11
"""

_STL_21 = """solid tooth21
  facet normal 0 0 1
    outer loop
      vertex 0.8 0 0
      vertex 1.8 0 0
      vertex 0.8 1 0
    endloop
  endfacet
endsolid tooth21
"""


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


def test_evaluation_loads_reviewed_workspace_triangles(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    asset_11 = _registered_stl(tmp_path, workspace, "11.stl", _STL_11)
    asset_21 = _registered_stl(tmp_path, workspace, "21.stl", _STL_21)
    payload = _workspace_collision_payload(asset_11, asset_21, reviewed=True)

    result = evaluate_plan_payload(payload, workspace=workspace)

    assert result["ok"] is True
    message = _collision_message(result)
    assert "Minimum triangle-surface distance is 0.000 mm" in message


def test_evaluation_keeps_unreviewed_workspace_triangles_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    asset_11 = _registered_stl(tmp_path, workspace, "11.stl", _STL_11)
    asset_21 = _registered_stl(tmp_path, workspace, "21.stl", _STL_21)
    payload = _workspace_collision_payload(asset_11, asset_21, reviewed=False)

    result = evaluate_plan_payload(payload, workspace=workspace)

    assert result["ok"] is True
    message = _collision_message(result)
    assert "Minimum representative-surface distance is 1.414 mm" in message


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


def _registered_stl(tmp_path: Path, workspace: Path, filename: str, text: str) -> MeshAsset:
    source = tmp_path / filename
    source.write_text(text, encoding="utf-8")
    asset = register_stl_mesh(source, workspace=workspace)
    return asset.model_copy(
        update={
            "bounds": BoundingBox(
                min_xyz=(asset.bounds.min_xyz[0], asset.bounds.min_xyz[1], -0.01),
                max_xyz=(asset.bounds.max_xyz[0], asset.bounds.max_xyz[1], 0.01),
            )
        }
    )


def _workspace_collision_payload(asset_11: MeshAsset, asset_21: MeshAsset, *, reviewed: bool) -> dict:
    return {
        "id": "workspace-contact",
        "mesh_assets": [
            asset_11.model_dump(mode="json"),
            asset_21.model_dump(mode="json"),
        ],
        "tooth_meshes": [
            {
                "tooth": {"system": "FDI", "value": "11"},
                "mesh_asset_id": asset_11.id,
                "reviewed": reviewed,
                "surface_sample_points": [(0.0, 0.0, 0.0)],
            },
            {
                "tooth": {"system": "FDI", "value": "21"},
                "mesh_asset_id": asset_21.id,
                "reviewed": reviewed,
                "surface_sample_points": [(1.0, 1.0, 0.0)],
            },
        ],
        "stages": [{"index": 0, "deltas": []}],
    }


def _collision_message(result: dict) -> str:
    finding = next(
        finding
        for finding in result["findings"]
        if finding["code"] == "segmented-crown-sample-contact"
    )
    return finding["message"]
