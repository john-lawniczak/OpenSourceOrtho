from __future__ import annotations

import pytest

from orthoplan.api import evaluate_plan
from orthoplan.model.anatomy import (
    AlveolarBoneRecord,
    DerivedAnatomy,
    ReviewStatus,
    RootGeometry,
    ToothAxis,
)
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.model.review_tier import ReviewTier, cbct_status, review_tier, root_bone_aware_ready


def _scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id="scan", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )


def _cbct() -> CaseRecord:
    return CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")


def _accepted_reg() -> RegistrationTransform:
    return RegistrationTransform(
        id="reg1", source_stl_asset_id="scan", target_cbct_record_id="cb",
        quality=RegistrationQuality(method="manual", rmse_mm=0.2), accepted=True,
    )


def _root(status: ReviewStatus, *, out_of_field: bool = False, tooth: str = "11") -> RootGeometry:
    return RootGeometry(
        tooth={"system": "FDI", "value": tooth},
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=status, out_of_field=out_of_field,
        centerline=[(0, 0, 0), (0, 0, 10)],
    )


def test_review_status_drives_reviewed_and_trusted() -> None:
    assert _root(ReviewStatus.PROPOSED).trusted is False
    assert _root(ReviewStatus.REJECTED).trusted is False
    assert _root(ReviewStatus.ACCEPTED).trusted is True
    assert _root(ReviewStatus.CORRECTED).trusted is True
    # In field is required: an accepted-but-out-of-field object is not trusted.
    assert _root(ReviewStatus.ACCEPTED, out_of_field=True).trusted is False


def test_plan_rejects_anatomy_with_unknown_references() -> None:
    with pytest.raises(ValueError, match="unknown registration"):
        TreatmentPlan(
            id="p", scans=[_scan()], case_records=[_cbct()],
            registrations=[_accepted_reg()],
            derived_anatomy=DerivedAnatomy(roots=[
                RootGeometry(
                    tooth={"system": "FDI", "value": "11"},
                    source_cbct_record_id="cb", registration_id="missing",
                )
            ]),
        )


def _root_bone_plan(status: ReviewStatus, *, out_of_field: bool = False) -> TreatmentPlan:
    return TreatmentPlan(
        id="p", scans=[_scan()], case_records=[_cbct()],
        registrations=[_accepted_reg()],
        derived_anatomy=DerivedAnatomy(roots=[_root(status, out_of_field=out_of_field)]),
    )


def test_root_bone_aware_only_when_registration_and_trusted_anatomy() -> None:
    accepted = _root_bone_plan(ReviewStatus.ACCEPTED)
    assert root_bone_aware_ready(accepted) is True
    assert review_tier(accepted) is ReviewTier.ROOT_BONE_AWARE
    assert cbct_status(accepted).value == "anatomy-reviewed"


def test_proposed_or_out_of_field_anatomy_is_fail_closed() -> None:
    proposed = _root_bone_plan(ReviewStatus.PROPOSED)
    assert root_bone_aware_ready(proposed) is False
    assert review_tier(proposed) is ReviewTier.CBCT_ATTACHED

    out_of_field = _root_bone_plan(ReviewStatus.ACCEPTED, out_of_field=True)
    assert root_bone_aware_ready(out_of_field) is False


def test_evaluate_exposes_per_object_trust_flags() -> None:
    plan = TreatmentPlan(
        id="p", scans=[_scan()], case_records=[_cbct()],
        registrations=[_accepted_reg()],
        derived_anatomy=DerivedAnatomy(
            roots=[_root(ReviewStatus.ACCEPTED)],
            tooth_axes=[ToothAxis(
                tooth={"system": "FDI", "value": "11"},
                origin_mm=(0, 0, 0), direction=(0, 0, 1),
                source_cbct_record_id="cb", registration_id="reg1",
                review_status=ReviewStatus.PROPOSED,
            )],
            alveolar_bone=[AlveolarBoneRecord(
                source_cbct_record_id="cb", registration_id="reg1",
                review_status=ReviewStatus.ACCEPTED,
            )],
        ),
    )
    block = evaluate_plan(plan)["derived_anatomy"]
    assert block["has_trusted"] is True
    assert block["roots"][0]["trusted"] is True
    assert block["tooth_axes"][0]["trusted"] is False  # only proposed
    assert block["alveolar_bone"][0]["trusted"] is True
