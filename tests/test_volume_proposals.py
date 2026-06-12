from __future__ import annotations

import pytest

from orthoplan.evaluation.rules.root_bone import RootBoneVerdict, root_bone_review
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.model.review_tier import ReviewTier, review_tier, root_bone_aware_ready
from orthoplan.registration_auto import RegistrationProposal
from orthoplan.volume_proposals import (
    VolumeProposalInput,
    VolumeProposalUnavailable,
    propose_cbct_anatomy_from_volume,
)


def _cbct() -> CaseRecord:
    return CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")


def _scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(
            id="scan",
            format="stl",
            units=MeshUnits.MM,
            vertex_count=3,
            face_count=1,
        )
    )


def _reg(*, accepted: bool = True) -> RegistrationTransform:
    return RegistrationTransform(
        id="reg",
        source_stl_asset_id="scan",
        target_cbct_record_id="cb",
        quality=RegistrationQuality(method="manual", rmse_mm=0.2, fitness=0.9),
        accepted=accepted,
    )


def test_volume_path_proposes_roots_axes_and_bone_only() -> None:
    proposal = propose_cbct_anatomy_from_volume(
        VolumeProposalInput(
            cbct_record=_cbct(),
            registration=_reg(),
            root_voxels_by_tooth={"11": [(2, 2, z) for z in range(4)]},
            bone_voxels=[(x, 0, 0) for x in range(12)],
            voxel_spacing_mm=(0.25, 0.25, 0.5),
        )
    )

    assert len(proposal.roots) == 1
    assert len(proposal.tooth_axes) == 1
    assert len(proposal.alveolar_bone) == 1
    assert all(obj.review_status == "proposed" for obj in proposal.all_objects())
    assert all(obj.trusted is False for obj in proposal.all_objects())
    assert proposal.roots[0].quality_metrics["voxel_count"] == 4
    assert proposal.roots[0].quality_metrics["centerline_points"] == 4


def test_volume_path_requires_accepted_registration() -> None:
    with pytest.raises(VolumeProposalUnavailable):
        propose_cbct_anatomy_from_volume(
            VolumeProposalInput(
                cbct_record=_cbct(),
                registration=_reg(accepted=False),
                root_voxels_by_tooth={"11": [(0, 0, 0)]},
                bone_voxels=[],
            )
        )


def test_proposed_volume_anatomy_never_promotes_root_bone_behavior() -> None:
    anatomy = propose_cbct_anatomy_from_volume(
        VolumeProposalInput(
            cbct_record=_cbct(),
            registration=_reg(),
            root_voxels_by_tooth={"11": [(1, 1, z) for z in range(5)]},
            bone_voxels=[(x, 0, 0) for x in range(10)],
        )
    )
    plan = TreatmentPlan(
        id="p",
        scans=[_scan()],
        case_records=[_cbct()],
        registrations=[_reg()],
        derived_anatomy=anatomy,
    )

    assert root_bone_aware_ready(plan) is False
    assert review_tier(plan) is ReviewTier.CBCT_ATTACHED
    assert root_bone_review(plan).verdict is RootBoneVerdict.NOT_APPLICABLE


def test_registration_proposal_is_unaccepted_review_packet() -> None:
    transform = _reg(accepted=False).model_copy(update={"method": "automatic-icp"})
    proposal = RegistrationProposal(transform=transform, status="proposed")

    assert proposal.requires_human_acceptance is True
    assert proposal.transform.accepted is False
    assert proposal.transform.is_acceptable is False


def test_volume_path_filters_small_disconnected_root_components() -> None:
    proposal = propose_cbct_anatomy_from_volume(
        VolumeProposalInput(
            cbct_record=_cbct(),
            registration=_reg(),
            root_voxels_by_tooth={
                "11": [(4, 4, z) for z in range(5)] + [(20, 20, 20), (25, 25, 25)],
            },
            bone_voxels=[],
            min_root_component_voxels=3,
        )
    )
    root = proposal.roots[0]

    assert root.quality_metrics["input_voxel_count"] == 7
    assert root.quality_metrics["voxel_count"] == 5
    assert root.quality_metrics["component_count"] == 3
    assert root.quality_metrics["dropped_component_count"] == 2
    assert any("dropped 2 small disconnected" in note for note in root.notes)


def test_volume_path_flags_field_boundary_truncation() -> None:
    proposal = propose_cbct_anatomy_from_volume(
        VolumeProposalInput(
            cbct_record=_cbct(),
            registration=_reg(),
            root_voxels_by_tooth={"11": [(0, 4, z) for z in range(4)]},
            bone_voxels=[(x, 0, z) for x in range(4) for z in range(4)],
            volume_dimensions=(8, 8, 8),
        )
    )

    assert proposal.roots[0].out_of_field is True
    assert proposal.tooth_axes[0].out_of_field is True
    assert proposal.alveolar_bone[0].out_of_field is True
    assert proposal.roots[0].quality_metrics["touches_volume_boundary"] is True
    assert any("field boundary" in note for note in proposal.roots[0].notes)
