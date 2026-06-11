from __future__ import annotations

from orthoplan.cases import summarize_provenance
from orthoplan.model.assets import (
    BoundingBox,
    CaseRecord,
    MeshAsset,
    MeshProvenance,
    MeshUnits,
    UploadedScan,
)
from orthoplan.model.plan import DataAvailability, TreatmentPlan
from orthoplan.model.review_tier import ReviewTier, review_tier, review_tier_info


def _mm_scan(asset_id: str = "scan-1", arch: str = "maxillary") -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(
            id=asset_id,
            format="stl",
            units=MeshUnits.MM,
            vertex_count=100,
            face_count=180,
            bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(50, 40, 20)),
        ),
        arch=arch,
    )


def _record(kind: str, record_id: str, modality: str | None = None) -> CaseRecord:
    return CaseRecord(id=record_id, kind=kind, modality=modality)


def test_stl_only_when_just_surface_scans() -> None:
    plan = TreatmentPlan(id="p", scans=[_mm_scan()])
    assert review_tier(plan) is ReviewTier.STL_ONLY


def test_enhanced_records_from_photos_and_notes() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[_mm_scan()],
        case_records=[_record("photo", "ph1"), _record("note", "nt1")],
    )
    assert review_tier(plan) is ReviewTier.ENHANCED_RECORDS


def test_cbct_attachment_classifies_as_attached_not_root_bone_aware() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[_mm_scan()],
        case_records=[_record("cbct", "cb1", modality="CT")],
    )
    assert review_tier(plan) is ReviewTier.CBCT_ATTACHED


def test_data_availability_flags_never_promote_to_root_bone_aware() -> None:
    # Safety: bare DataAvailability booleans must not unlock root/bone-aware review;
    # that tier is fail-closed until registration + reviewed anatomy exist.
    plan = TreatmentPlan(
        id="p",
        scans=[_mm_scan()],
        data=DataAvailability(roots=True, cbct=True, periodontal_status=True),
    )
    info = review_tier_info(plan)
    assert info.tier is ReviewTier.CBCT_ATTACHED
    assert info.root_bone_aware is False


def test_provenance_summary_captures_units_arch_modality_and_tier() -> None:
    plan = TreatmentPlan(
        id="p",
        scans=[_mm_scan("scan-A", "mandibular")],
        mesh_assets=[
            MeshAsset(
                id="seg-1",
                format="stl",
                provenance=MeshProvenance.MODEL_GENERATED,
                units=MeshUnits.MM,
                vertex_count=10,
                face_count=12,
            )
        ],
        case_records=[_record("cbct", "cb1", modality="CT")],
    )
    prov = summarize_provenance(plan)
    assert prov.review_tier == ReviewTier.CBCT_ATTACHED.value
    assert prov.units_confirmed is True
    assert prov.scans[0].arch == "mandibular"
    assert prov.scans[0].units == "mm"
    assert prov.records[0].modality == "CT"
    assert set(prov.mesh_asset_ids) == {"scan-A", "seg-1"}


def test_unverified_units_mark_provenance_unconfirmed() -> None:
    scan = UploadedScan(
        asset=MeshAsset(id="raw", format="stl", vertex_count=1, face_count=1),
    )
    plan = TreatmentPlan(id="p", scans=[scan])
    prov = summarize_provenance(plan)
    assert prov.units_confirmed is False
    assert prov.scans[0].units_confirmed is False
