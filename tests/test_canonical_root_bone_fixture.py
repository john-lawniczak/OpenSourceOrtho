from __future__ import annotations

import json
from pathlib import Path

from orthoplan.io.stl_import import inspect_stl
from orthoplan.model.assets import MeshUnits, UploadedScan
from orthoplan.model.plan import SegmentedToothMesh, Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.registration_gate import RegistrationGateVerdict, gate_registrations
from orthoplan.model.review_tier import ReviewTier, cbct_status, review_tier
from orthoplan.planning.anatomical_frame import trusted_axis_frames
from orthoplan.evaluation.rules.root_bone import RootBoneVerdict, root_bone_review
from orthoplan.segmentation.cbct_prior import boundary_priors_for_arch

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "ui" / "example-scans" / "canonical-orthocad-001"


def _fixture() -> dict:
    return json.loads((CASE_DIR / "root-bone-fixture.json").read_text(encoding="utf-8"))


def _sample_plan() -> TreatmentPlan:
    fixture = _fixture()
    upper = inspect_stl(CASE_DIR / "sample-test-case-upper.stl").model_copy(
        update={"units": MeshUnits.MM}
    )
    lower = inspect_stl(CASE_DIR / "sample-test-case-lower.stl").model_copy(
        update={"units": MeshUnits.MM}
    )
    return TreatmentPlan(
        id="canonical-orthocad-001-root-bone-fixture",
        scans=[
            UploadedScan(asset=upper, arch="maxillary"),
            UploadedScan(asset=lower, arch="mandibular"),
        ],
        case_records=fixture["case_records"],
        mesh_assets=fixture["mesh_assets"],
        registrations=fixture["registrations"],
        derived_anatomy=fixture["derived_anatomy"],
    )


def test_canonical_root_bone_fixture_validates_and_opens_review_tier() -> None:
    plan = _sample_plan()

    assert review_tier(plan) is ReviewTier.ROOT_BONE_AWARE
    assert cbct_status(plan).value == "anatomy-reviewed"
    assert len(plan.derived_anatomy.roots) == 12
    assert len(plan.derived_anatomy.tooth_axes) == 12
    assert plan.derived_anatomy.has_trusted is True


def test_canonical_fixture_registration_gates_pass() -> None:
    gates = {gate.registration_id: gate for gate in gate_registrations(_sample_plan())}

    assert gates["reg-canonical-upper-to-cbct"].verdict is RegistrationGateVerdict.PASS
    assert gates["reg-canonical-lower-to-cbct"].verdict is RegistrationGateVerdict.PASS


def test_canonical_fixture_supplies_cbct_boundary_priors() -> None:
    plan = _sample_plan()
    upper = boundary_priors_for_arch(plan, "maxillary")
    lower = boundary_priors_for_arch(plan, "mandibular")

    assert upper is not None
    assert lower is not None
    assert upper.tooth_pairs == [("13", "12"), ("12", "11"), ("11", "21"), ("21", "22"), ("22", "23")]
    assert lower.tooth_pairs == [("43", "42"), ("42", "41"), ("41", "31"), ("31", "32"), ("32", "33")]
    assert upper.allow_confidence_boost is True
    assert lower.allow_confidence_boost is True


def test_canonical_fixture_drives_root_bone_review_after_segmentation() -> None:
    fixture = _fixture()
    plan = _sample_plan()
    teeth = ["13", "12", "11", "21", "22", "23", "43", "42", "41", "31", "32", "33"]
    mesh_assets = [
        {
            "id": f"fixture-seg-{tooth}",
            "format": "stl-ascii",
            "provenance": "model-generated",
            "units": "mm",
            "vertex_count": 3,
            "face_count": 1,
        }
        for tooth in teeth
    ]
    roots_by_tooth = {
        root["tooth"]["value"]: root["centerline"][0]
        for root in fixture["derived_anatomy"]["roots"]
    }
    links = [
        SegmentedToothMesh(
            tooth=ToothId(value=tooth),
            mesh_asset_id=f"fixture-seg-{tooth}",
            reviewed=True,
            surface_sample_points=[
                (
                    roots_by_tooth[tooth][0] - 179.712454,
                    roots_by_tooth[tooth][1] - 23.020452,
                    roots_by_tooth[tooth][2] - 7.557038,
                )
            ],
        )
        for tooth in teeth
    ]
    stage = Stage(
        index=0,
        deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)],
    )
    plan = TreatmentPlan(
        id=plan.id,
        scans=plan.scans,
        case_records=plan.case_records,
        mesh_assets=[*fixture["mesh_assets"], *mesh_assets],
        registrations=plan.registrations,
        derived_anatomy=plan.derived_anatomy,
        tooth_meshes=links,
        stages=[stage],
    )

    frames = trusted_axis_frames(plan)
    review = root_bone_review(plan)

    assert "11" in frames
    assert frames["11"].approximate is False
    assert review.verdict is RootBoneVerdict.CONSISTENT
    assert any(f.code == "root-bone-context" for f in review.findings)


def test_canonical_fixture_does_not_track_raw_identifiers_or_absolute_paths() -> None:
    text = (CASE_DIR / "root-bone-fixture.json").read_text(encoding="utf-8")

    assert "/Users/" not in text
    assert "PatientName" not in text
    assert "PatientID" not in text
    assert "SeriesInstanceUID" not in text
    assert "StudyInstanceUID" not in text
