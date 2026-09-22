"""Evidence states remain separate from export and physical-use claims."""
from __future__ import annotations

import pytest

from orthoplan.api import evaluate_plan
from orthoplan.evaluation.intake_cbct import cbct_records
from orthoplan.evaluation.intake_records import segmentation_records, surface_records
from orthoplan.model.anatomy import DerivedAnatomy, RootGeometry
from orthoplan.model.assets import (
    BoundingBox, CaseRecord, MeshAsset, MeshQualityReport, MeshUnits, UploadedScan,
)
from orthoplan.model.plan import DataAvailability, SegmentedToothMesh, Stage, ToothDelta, TreatmentPlan
from orthoplan.model.readiness import IntakeReadiness
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform


def scan(asset_id="upper", arch="maxillary", **kwargs):
    fields = dict(id=asset_id, format="stl", units=MeshUnits.MM, vertex_count=3, face_count=1,
                  bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(60, 40, 20)),
                  quality=MeshQualityReport(degenerate_faces=0))
    fields.update(kwargs)
    return UploadedScan(asset=MeshAsset(**fields), arch=arch)


def indexed(items):
    return {item.id: item for item in items}


def test_empty_plan_does_not_inherit_optimistic_availability_defaults():
    result = evaluate_plan(TreatmentPlan(id="empty"))["intake_readiness"]
    report = IntakeReadiness.model_validate(result)
    records = indexed(report.records)
    assert records["arch:maxillary"].state == "missing"
    assert records["segmentation"].state == "missing"
    assert report.plan_consistency.status == "no_stages"
    assert report.artifacts.status == "blocked"
    assert report.artifacts.geometry_qa == "not_run"
    assert report.physical_validation == "not_assessed"


@pytest.mark.parametrize("changes,expected", [
    ({"units": MeshUnits.UNVERIFIED}, "millimeters"),
    ({"units": MeshUnits.CM}, "millimeters"),
    ({"bounds": None}, "bounds are unavailable"),
    ({"bounds": BoundingBox(min_xyz=(0, 0, 0), max_xyz=(600, 40, 20))}, "confirm scale"),
    ({"bounds": BoundingBox(min_xyz=(10, 0, 0), max_xyz=(0, 40, 20))}, "bounds are invalid"),
    ({"quality": None}, "not been inspected"),
    ({"quality": MeshQualityReport(degenerate_faces=5)}, "degeneracy"),
])
def test_problematic_scan_metadata_requires_review(changes, expected):
    records = indexed(surface_records(TreatmentPlan(id="p", scans=[scan(**changes)])))
    assert records["scan:upper"].state == "needs_review"
    assert expected in records["scan:upper"].detail


def test_partial_unlabeled_and_conflicting_arches():
    plan = TreatmentPlan(id="p", scans=[scan(), scan("other"), scan("unknown", None)])
    records = indexed(surface_records(plan))
    assert records["arch:maxillary"].state == "needs_review"
    assert records["arch:mandibular"].state == "missing"
    assert records["scan:unknown"].state == "needs_review"


def test_two_arch_records_do_not_imply_segmentation_or_bite_evidence():
    plan = TreatmentPlan(id="p", scans=[scan(), scan("lower", "mandibular")],
                         data=DataAvailability(segmented_teeth=True, occlusion_scan=True, cbct=True))
    report = IntakeReadiness.model_validate(evaluate_plan(plan)["intake_readiness"])
    records = indexed(report.records)
    assert records["arch:maxillary"].state == records["arch:mandibular"].state == "present"
    assert records["segmentation"].state == "missing"
    assert records["bite"].state == "needs_review"
    assert records["cbct"].state == "missing"


def test_partial_review_does_not_cover_other_moving_teeth():
    plan = TreatmentPlan(id="p", mesh_assets=[scan().asset],
        tooth_meshes=[SegmentedToothMesh(tooth={"value": "11"}, mesh_asset_id="upper", reviewed=True)],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"value": "12"}, translate_x_mm=.1)])])
    records = indexed(segmentation_records(plan))
    assert records["segmentation"].state == "needs_review"
    assert "12" in records["segmentation"].detail
    assert records["segmentation_quality"].state == "not_assessed"


def test_export_prerequisites_never_mean_qa_or_physical_validation():
    plan = TreatmentPlan(id="p", data=DataAvailability(segmented_teeth=True),
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"value": "11"}, translate_x_mm=.1)])])
    plan.settings.print_export.enabled = True
    plan.settings.print_export.safety_acknowledged = True
    report = IntakeReadiness.model_validate(evaluate_plan(plan)["intake_readiness"])
    assert report.artifacts.status == "prerequisites_met"
    assert report.artifacts.geometry_qa == "not_run"
    assert report.physical_validation == "not_assessed"
    assert indexed(report.records)["segmentation"].state == "missing"


def test_registration_trust_is_bound_to_each_anatomy_objects_own_registration():
    registrations = [RegistrationTransform(id=name, source_stl_asset_id="upper", target_cbct_record_id="cb",
        accepted=True, quality=RegistrationQuality(method="fixture", rmse_mm=rmse))
        for name, rmse in [("good", .2), ("bad", 2.0)]]
    root = RootGeometry(tooth={"value": "11"}, source_cbct_record_id="cb", registration_id="bad",
                        review_status="accepted", centerline=[(0, 0, 0), (0, 0, 10)])
    plan = TreatmentPlan(id="p", scans=[scan()], case_records=[CaseRecord(id="cb", kind="cbct")],
                        registrations=registrations, derived_anatomy=DerivedAnatomy(roots=[root]))
    records = indexed(cbct_records(plan))
    assert records["registration:good"].state == "present"
    assert records["registration:bad"].state == "blocked"
    assert records["anatomy:roots"].state == "blocked"
    root.registration_id = "good"
    assert indexed(cbct_records(plan))["anatomy:roots"].state == "present"
    root.out_of_field = True
    assert indexed(cbct_records(plan))["anatomy:roots"].state == "blocked"


def test_scale_limited_plan_checks_are_distinct_from_missing_cbct():
    plan = TreatmentPlan(id="p", scans=[scan(units=MeshUnits.UNVERIFIED)], stages=[Stage(index=0)])
    report = IntakeReadiness.model_validate(evaluate_plan(plan)["intake_readiness"])
    assert report.plan_consistency.status == "limited"
    assert indexed(report.records)["cbct"].state == "missing"
