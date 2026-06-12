from __future__ import annotations

from orthoplan.cbct_workflow import cbct_proposal_payload, cbct_review_payload, cbct_summary_payload
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import TreatmentPlan


def _plan() -> TreatmentPlan:
    return TreatmentPlan(
        id="cbct-workflow",
        scans=[
            UploadedScan(
                asset=MeshAsset(
                    id="scan",
                    format="stl",
                    units=MeshUnits.MM,
                    vertex_count=3,
                    face_count=1,
                )
            )
        ],
        case_records=[
            CaseRecord(id="cb", kind="cbct", modality="CBCT/DICOM", local_reference="records/cb.dcm")
        ],
    )


def _payload(**overrides):
    payload = {
        "plan": _plan().model_dump(mode="json"),
        "cbct_record_id": "cb",
        "source_stl_asset_id": "scan",
        "registration_accepted": True,
        "registration_quality": {"method": "imported", "rmse_mm": 0.2, "fitness": 0.92},
        "mask": {
            "root_voxels_by_tooth": {"11": [[2, 2, z] for z in range(2, 6)]},
            "bone_voxels": [[x, 2, 2] for x in range(2, 6) for _ in range(3)],
            "voxel_spacing_mm": [0.25, 0.25, 0.5],
            "volume_dimensions": [8, 8, 8],
        },
    }
    payload.update(overrides)
    return payload


def test_cbct_summary_lists_inspectable_records() -> None:
    result = cbct_summary_payload({"plan": _plan().model_dump(mode="json")})

    assert result["ok"] is True
    assert result["ready"]["has_cbct"] is True
    assert result["cbct_records"][0]["id"] == "cb"


def test_cbct_mask_import_creates_untrusted_anatomy_proposals() -> None:
    result = cbct_proposal_payload(_payload())

    assert result["ok"] is True
    assert result["registration"]["accepted"] is True
    assert len(result["proposal"]["roots"]) == 1
    assert result["proposal"]["roots"][0]["review_status"] == "proposed"
    assert result["proposal"]["roots"][0]["trusted"] is False
    assert result["proposal"]["alveolar_bone"][0]["trusted"] is False
    assert result["plan"]["derived_anatomy"]["roots"][0]["quality_metrics"]["centerline_points"] == 4


def test_cbct_mask_import_requires_accepted_quality_backed_registration() -> None:
    result = cbct_proposal_payload(
        _payload(registration_accepted=False, registration_quality={"method": "imported"})
    )

    assert result["ok"] is False
    assert "accepted registration" in result["errors"][0]


def test_cbct_review_decisions_are_required_before_trust() -> None:
    proposed = cbct_proposal_payload(_payload())["plan"]
    result = cbct_review_payload(
        {
            "plan": proposed,
            "decisions": [
                {"group": "roots", "index": 0, "review_status": "accepted"},
                {"group": "tooth_axes", "index": 0, "review_status": "accepted"},
                {"group": "alveolar_bone", "index": 0, "review_status": "rejected"},
            ],
        }
    )

    assert result["ok"] is True
    assert result["trusted_count"] == 2
    assert result["derived_anatomy"]["roots"][0]["trusted"] is True
    assert result["derived_anatomy"]["alveolar_bone"][0]["trusted"] is False
