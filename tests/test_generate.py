from __future__ import annotations

from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.model.assets import BoundingBox, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.clinical import FixedTooth
from orthoplan.model.landmarks import ArchLandmarks, CrownLandmark
from orthoplan.model.plan import SegmentedToothMesh, Stage, ToothDelta, TreatmentPlan
from orthoplan.planning.generate import generate_plan


def _confirmed_scan(asset_id: str = "scan-1") -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id=asset_id, format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0)
    )


def _no_cap_violations(plan: TreatmentPlan) -> bool:
    return not any("exceeds configured" in f.title for f in evaluate_movement_caps(plan))


def test_authored_targets_are_restaged_within_caps() -> None:
    # A single 1.0 mm move exceeds the 0.25 mm linear cap and must be split.
    plan = TreatmentPlan(
        id="p",
        scans=[_confirmed_scan()],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"system": "FDI", "value": "21"}, translate_x_mm=1.0)])],
    )
    result = generate_plan(plan)
    assert result.source == "authored"
    assert not result.requires_acknowledgement
    assert len(result.plan.stages) >= 4  # 1.0 / 0.25
    assert _no_cap_violations(result.plan)
    assert result.aligned_tooth_count == 1


def test_educational_synthetic_fallback_when_only_raw_scan() -> None:
    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()])
    result = generate_plan(plan)
    assert result.source == "educational-synthetic"
    assert result.requires_acknowledgement is True
    assert result.target_tooth_count == 12
    assert any("EDUCATIONAL" in w for w in result.warnings)
    assert _no_cap_violations(result.plan)


def test_acknowledgement_clears_requirement() -> None:
    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()])
    result = generate_plan(plan, acknowledge_educational=True)
    assert result.source == "educational-synthetic"
    assert result.requires_acknowledgement is False


def test_fixed_tooth_is_not_moved_by_generator() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[_confirmed_scan()],
        fixed_teeth=[FixedTooth(tooth={"system": "FDI", "value": "11"})],
    )
    result = generate_plan(plan)
    assert "11" in result.blocked_teeth
    moved = {d.tooth.value for stage in result.plan.stages for d in stage.deltas}
    assert "11" not in moved


def test_geometry_derived_targets_from_segmented_crowns() -> None:
    # Four maxillary crowns; one (12) sits off a smooth curve so it gets corrected.
    assets = [
        MeshAsset(id="m11", format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0,
                  bounds=BoundingBox(min_xyz=(-2, 8, 0), max_xyz=(2, 12, 6))),
        MeshAsset(id="m12", format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0,
                  bounds=BoundingBox(min_xyz=(6, 4, 0), max_xyz=(10, 10, 6))),
        MeshAsset(id="m13", format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0,
                  bounds=BoundingBox(min_xyz=(12, 2, 0), max_xyz=(16, 6, 6))),
        MeshAsset(id="m14", format="stl", units=MeshUnits.MM, vertex_count=0, face_count=0,
                  bounds=BoundingBox(min_xyz=(18, -2, 0), max_xyz=(22, 2, 6))),
    ]
    links = [
        SegmentedToothMesh(tooth={"system": "FDI", "value": v}, mesh_asset_id=a)
        for v, a in [("11", "m11"), ("12", "m12"), ("13", "m13"), ("14", "m14")]
    ]
    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()], mesh_assets=assets, tooth_meshes=links)
    result = generate_plan(plan)
    assert result.source == "geometry-derived"
    assert result.target_tooth_count >= 1
    assert any("geometric" in w for w in result.warnings)
    assert _no_cap_violations(result.plan)


def _landmarks() -> ArchLandmarks:
    # Tight upper anterior arch with one incisor pulled off the curve.
    rows = [("13", -6, 1.2), ("12", -4, 0.6), ("11", -2, 0.6), ("21", 0, 0.0), ("22", 2, 0.2), ("23", 4, 0.8)]
    return ArchLandmarks(landmarks=[
        CrownLandmark(tooth={"system": "FDI", "value": v}, x_mm=x, y_mm=y) for v, x, y in rows
    ])


def test_landmark_derived_source_and_clinical_structure() -> None:
    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()])
    result = generate_plan(plan, landmarks=_landmarks())
    assert result.source == "landmark-derived"
    assert result.plan.interproximal_reductions  # space budget emitted
    assert result.plan.attachments  # attachments on moved teeth
    assert len(result.plan.tooth_meshes) == 6  # approximate collision bounds present
    assert result.space_discrepancy_mm is not None and result.space_discrepancy_mm > 0
    assert _no_cap_violations(result.plan)


def test_landmark_collision_check_is_no_longer_vacuous() -> None:
    from orthoplan.evaluation.rules.collisions import evaluate_segmented_mesh_collisions

    plan = TreatmentPlan(id="p", scans=[_confirmed_scan()])
    result = generate_plan(plan, landmarks=_landmarks())
    # With per-tooth bounds present the collision rule actually evaluates pairs
    # (it returns [] only when < 2 segmented teeth exist).
    assert len(result.plan.tooth_meshes) >= 2
    evaluate_segmented_mesh_collisions(result.plan)  # must run without error


def test_authored_movement_takes_priority_over_landmarks() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[_confirmed_scan()],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"system": "FDI", "value": "21"}, translate_x_mm=0.5)])],
    )
    result = generate_plan(plan, landmarks=_landmarks())
    assert result.source == "authored"


def test_no_targets_returns_none_source() -> None:
    plan = TreatmentPlan(id="p")  # no scans, no stages, no meshes
    result = generate_plan(plan)
    assert result.source == "none"
    assert result.plan.stages == []
