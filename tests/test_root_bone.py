from __future__ import annotations

from orthoplan.evaluation.rules.root_bone import RootBoneVerdict, root_bone_review
from orthoplan.model.anatomy import (
    AlveolarBoneRecord,
    DerivedAnatomy,
    ReviewStatus,
    RootGeometry,
)
from orthoplan.model.assets import BoundingBox, CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import SegmentedToothMesh, Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform


def _scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id="scan", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )


def _cbct() -> CaseRecord:
    return CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")


def _reg() -> RegistrationTransform:
    return RegistrationTransform(
        id="reg1", source_stl_asset_id="scan", target_cbct_record_id="cb",
        quality=RegistrationQuality(method="manual", rmse_mm=0.2), accepted=True,
    )


def _root(tooth: str, x: float) -> RootGeometry:
    return RootGeometry(
        tooth={"system": "FDI", "value": tooth},
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=ReviewStatus.ACCEPTED,
        centerline=[(x, 0, 0), (x, 0, -10)],
    )


def _seg_assets(teeth):
    assets = [
        MeshAsset(id=f"seg-{t}", format="stl-ascii", units=MeshUnits.MM, vertex_count=3, face_count=1,
                  bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(1, 1, 1)))
        for t in teeth
    ]
    links = [SegmentedToothMesh(tooth=ToothId(value=t), mesh_asset_id=f"seg-{t}") for t in teeth]
    return assets, links


def test_stl_only_plan_is_not_applicable_and_silent() -> None:
    plan = TreatmentPlan(id="p", scans=[_scan()])
    review = root_bone_review(plan)
    assert review.verdict is RootBoneVerdict.NOT_APPLICABLE
    assert review.findings == []


def test_cbct_attached_but_not_ready_emits_cannot_assess() -> None:
    plan = TreatmentPlan(id="p", scans=[_scan()], case_records=[_cbct()])
    review = root_bone_review(plan)
    assert review.verdict is RootBoneVerdict.NOT_APPLICABLE
    assert any(f.code == "root-bone-not-applicable" for f in review.findings)


def _ready_plan(roots, *, bone=None, stages=None, teeth=("11", "12")) -> TreatmentPlan:
    assets, links = _seg_assets(teeth)
    if bone is not None:
        assets = [*assets, bone[0]]
    anatomy = DerivedAnatomy(roots=roots, alveolar_bone=[bone[1]] if bone else [])
    return TreatmentPlan(
        id="p", scans=[_scan()], case_records=[_cbct()], registrations=[_reg()],
        mesh_assets=assets, tooth_meshes=links, derived_anatomy=anatomy,
        stages=stages or [],
    )


def test_close_roots_flag_proximity_and_issues_verdict() -> None:
    plan = _ready_plan([_root("11", 0.0), _root("12", 0.5)])
    review = root_bone_review(plan)
    assert review.verdict is RootBoneVerdict.ISSUES
    assert any(f.code == "root-proximity" for f in review.findings)


def test_far_roots_without_bone_report_cortical_cannot_assess() -> None:
    plan = _ready_plan([_root("11", 0.0), _root("12", 5.0)])
    review = root_bone_review(plan)
    # Root proximity is consistent; cortical cannot be assessed without bone.
    assert not any(f.code == "root-proximity" for f in review.findings)
    assert any(f.code == "root-bone-not-applicable" for f in review.findings)
    assert review.verdict is RootBoneVerdict.CONSISTENT


def test_root_pushed_past_bone_boundary_flags_cortical() -> None:
    bone_asset = MeshAsset(
        id="bone", format="stl-ascii", units=MeshUnits.MM, vertex_count=8, face_count=12,
        bounds=BoundingBox(min_xyz=(-2, -2, -12), max_xyz=(2, 2, 2)),
    )
    bone_record = AlveolarBoneRecord(
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=ReviewStatus.ACCEPTED, mesh_asset_id="bone",
    )
    plan = _ready_plan(
        [_root("11", 0.0)],
        bone=(bone_asset, bone_record),
        teeth=("11",),
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=5.0)])],
    )
    review = root_bone_review(plan)
    assert any(f.code == "cortical-proximity" for f in review.findings)
    assert review.verdict is RootBoneVerdict.ISSUES


def test_movement_context_emitted_for_reviewed_root_with_movement() -> None:
    plan = _ready_plan(
        [_root("11", 0.0), _root("12", 5.0)],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_torque_deg=1.0)])],
    )
    review = root_bone_review(plan)
    assert any(f.code == "root-bone-context" for f in review.findings)


def test_apex_displacement_info_for_small_angulation() -> None:
    # 10 mm root, 2 deg torque -> apex sweep ~0.35 mm: documented, not flagged.
    plan = _ready_plan(
        [_root("11", 0.0), _root("12", 5.0)],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_torque_deg=2.0)])],
    )
    review = root_bone_review(plan)
    apex = [f for f in review.findings if f.code == "root-apex-displacement"]
    assert len(apex) == 1
    assert apex[0].severity.value == "info"
    assert "0.35 mm" in apex[0].message


def test_apex_displacement_warns_beyond_review_threshold() -> None:
    # 10 mm root, 10+10 deg of tip+torque over two stages -> sweep > 2 mm.
    stages = [
        Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=10.0)]),
        Stage(index=1, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_torque_deg=10.0)]),
    ]
    plan = _ready_plan([_root("11", 0.0), _root("12", 5.0)], stages=stages)
    review = root_bone_review(plan)
    apex = [f for f in review.findings if f.code == "root-apex-displacement"]
    assert len(apex) == 1
    assert apex[0].severity.value == "warning"
    assert review.verdict is RootBoneVerdict.ISSUES


def test_apex_displacement_silent_without_angulation() -> None:
    plan = _ready_plan(
        [_root("11", 0.0), _root("12", 5.0)],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )
    review = root_bone_review(plan)
    assert not any(f.code == "root-apex-displacement" for f in review.findings)
