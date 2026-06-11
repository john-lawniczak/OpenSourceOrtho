from __future__ import annotations

import pytest

from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import (
    RegistrationMethod,
    RegistrationQuality,
    RegistrationTransform,
)
from orthoplan.model.review_tier import (
    CbctStatus,
    accepted_registration,
    cbct_status,
    registration_ready,
    root_bone_aware_ready,
)
from orthoplan.registration_auto import (
    RegistrationBackendUnavailable,
    auto_register_icp,
    open3d_available,
)


def _scan(asset_id: str = "scan") -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id=asset_id, format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )


def _cbct(record_id: str = "cb") -> CaseRecord:
    return CaseRecord(id=record_id, kind="cbct", local_reference="records/cb.dcm")


def _translation_matrix(dx: float, dy: float, dz: float):
    return [[1, 0, 0, dx], [0, 1, 0, dy], [0, 0, 1, dz], [0, 0, 0, 1]]


def _reg(*, accepted: bool, with_quality: bool, reg_id: str = "r1") -> RegistrationTransform:
    return RegistrationTransform(
        id=reg_id,
        source_stl_asset_id="scan",
        target_cbct_record_id="cb",
        method=RegistrationMethod.MANUAL,
        matrix=_translation_matrix(1.0, 0.0, 0.0),
        quality=RegistrationQuality(method="manual", rmse_mm=0.2, fitness=0.95) if with_quality else None,
        accepted=accepted,
    )


def test_matrix_must_be_4x4_with_affine_bottom_row() -> None:
    with pytest.raises(ValueError, match="4x4"):
        RegistrationTransform(
            id="r", source_stl_asset_id="scan", target_cbct_record_id="cb",
            matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        )
    with pytest.raises(ValueError, match="bottom row"):
        RegistrationTransform(
            id="r", source_stl_asset_id="scan", target_cbct_record_id="cb",
            matrix=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 2]],
        )


def test_acceptance_is_fail_closed_requires_quality() -> None:
    assert _reg(accepted=True, with_quality=True).is_acceptable is True
    assert _reg(accepted=True, with_quality=False).is_acceptable is False
    assert _reg(accepted=False, with_quality=True).is_acceptable is False


def test_plan_rejects_registration_with_unknown_references() -> None:
    with pytest.raises(ValueError, match="unknown source mesh asset"):
        TreatmentPlan(
            id="p", scans=[_scan()], case_records=[_cbct()],
            registrations=[RegistrationTransform(
                id="r", source_stl_asset_id="missing", target_cbct_record_id="cb",
            )],
        )
    with pytest.raises(ValueError, match="unknown CBCT/DICOM record"):
        TreatmentPlan(
            id="p", scans=[_scan()], case_records=[_cbct()],
            registrations=[RegistrationTransform(
                id="r", source_stl_asset_id="scan", target_cbct_record_id="nope",
            )],
        )


def test_registration_gating_drives_cbct_status() -> None:
    attached = TreatmentPlan(id="p", scans=[_scan()], case_records=[_cbct()])
    assert cbct_status(attached) is CbctStatus.ATTACHED
    assert registration_ready(attached) is False

    registered = TreatmentPlan(
        id="p", scans=[_scan()], case_records=[_cbct()],
        registrations=[_reg(accepted=True, with_quality=True)],
    )
    assert registration_ready(registered) is True
    assert accepted_registration(registered).id == "r1"
    assert cbct_status(registered) is CbctStatus.REGISTERED


def test_accepted_registration_alone_is_not_root_bone_aware() -> None:
    # Fail-closed: registration without reviewed anatomy must not unlock root/bone.
    registered = TreatmentPlan(
        id="p", scans=[_scan()], case_records=[_cbct()],
        registrations=[_reg(accepted=True, with_quality=True)],
    )
    assert root_bone_aware_ready(registered) is False


@pytest.mark.skipif(open3d_available(), reason="Open3D installed; tests the fail-closed path")
def test_auto_register_fails_closed_without_open3d() -> None:
    with pytest.raises(RegistrationBackendUnavailable):
        auto_register_icp(
            [(0, 0, 0)], [(0, 0, 0)],
            registration_id="r", source_stl_asset_id="scan", target_cbct_record_id="cb",
        )
