from __future__ import annotations

from orthoplan.api import evaluate_plan
from orthoplan.model import (
    BoundingBox,
    CaseRecord,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.model.anatomy import DerivedAnatomy, RootGeometry, ToothAxis
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.planning.mesh_transform import build_transformed_mesh_frames


def _asset(asset_id: str = "mesh-11") -> MeshAsset:
    return MeshAsset(
        id=asset_id,
        format="stl-ascii",
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(-1, -1, -1), max_xyz=(1, 1, 1)),
    )


def _cbct_record() -> CaseRecord:
    return CaseRecord(id="cbct", kind="cbct", local_reference="records/cbct.dcm")


def _accepted_registration() -> RegistrationTransform:
    return RegistrationTransform(
        id="reg",
        source_stl_asset_id="mesh-11",
        target_cbct_record_id="cbct",
        accepted=True,
        quality=RegistrationQuality(method="fixture", rmse_mm=0.1),
    )


def _trusted_anatomy() -> DerivedAnatomy:
    common = {
        "source_cbct_record_id": "cbct",
        "registration_id": "reg",
        "review_status": "accepted",
    }
    return DerivedAnatomy(
        roots=[
            RootGeometry(
                tooth=ToothId(value="11"),
                centerline=[(0.0, 0.0, 0.0), (0.0, 0.0, -3.0)],
                **common,
            )
        ],
        tooth_axes=[
            ToothAxis(
                tooth=ToothId(value="11"),
                origin_mm=(0.0, 0.0, 0.0),
                direction=(0.0, 0.0, 1.0),
                **common,
            )
        ],
    )


def _plan(*, anatomy: bool = False) -> TreatmentPlan:
    return TreatmentPlan(
        id="bio",
        mesh_assets=[_asset()],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        case_records=[_cbct_record()] if anatomy else [],
        registrations=[_accepted_registration()] if anatomy else [],
        derived_anatomy=_trusted_anatomy() if anatomy else None,
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=10.0)])],
    )


def test_untrusted_roots_leave_frame_output_unchanged() -> None:
    base = TreatmentPlan(
        id="bio",
        mesh_assets=[_asset()],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=10.0)])],
    )
    with_untrusted_cbct = TreatmentPlan(
        id="bio",
        mesh_assets=[_asset()],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        case_records=[_cbct_record()],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=10.0)])],
    )

    assert evaluate_plan(base)["frames"] == evaluate_plan(with_untrusted_cbct)["frames"]
    assert evaluate_plan(with_untrusted_cbct)["movement_model"]["mode"] == "crown-centroid"


def test_trusted_tip_moves_root_apex_opposite_crown() -> None:
    frames = build_transformed_mesh_frames(
        _plan(anatomy=True),
        {"mesh-11": [(0.0, 0.0, 1.0), (0.0, 0.0, -3.0)]},
    )

    crown, apex = frames[0].meshes[0].vertices

    assert crown[1] > 0
    assert apex[1] < 0
    assert frames[0].meshes[0].transform_note.startswith("Applied cumulative translation")
    assert evaluate_plan(_plan(anatomy=True))["movement_model"]["mode"] == "root-aware"
