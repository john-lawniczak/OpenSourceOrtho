from __future__ import annotations

from orthoplan.evaluation.rules import (
    evaluate_no_movement,
    evaluate_root_sensitive_movement,
    evaluate_segmentation_presence,
)
from orthoplan.model import (
    DataAvailability,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)


def _plan(delta: ToothDelta, **kwargs: object) -> TreatmentPlan:
    return TreatmentPlan(id="pc", stages=[Stage(index=0, deltas=[delta])], **kwargs)


# --- root-sensitive movement ---

def test_tip_movement_without_root_data_warns() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=0.5))
    findings = evaluate_root_sensitive_movement(plan)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].data_gap and findings[0].clinician_question


def test_intrusion_without_root_data_warns() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_z_mm=0.05))
    assert evaluate_root_sensitive_movement(plan)


def test_root_sensitive_suppressed_when_root_data_present() -> None:
    plan = _plan(
        ToothDelta(tooth=ToothId(value="11"), rotate_tip_deg=0.5),
        data=DataAvailability(cbct=True),
    )
    assert evaluate_root_sensitive_movement(plan) == []


def test_pure_horizontal_or_rotation_is_not_root_sensitive() -> None:
    horizontal = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.5))
    rotation = _plan(ToothDelta(tooth=ToothId(value="11"), rotate_rotation_deg=2.0))
    assert evaluate_root_sensitive_movement(horizontal) == []
    assert evaluate_root_sensitive_movement(rotation) == []


# --- segmentation presence ---

def test_movement_without_segmentation_notices() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2))
    findings = evaluate_segmentation_presence(plan)
    assert len(findings) == 1
    assert findings[0].severity == "notice"


def test_segmentation_present_suppresses_notice() -> None:
    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    plan = TreatmentPlan(
        id="seg",
        mesh_assets=[asset],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="m11")],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )
    assert evaluate_segmentation_presence(plan) == []


def test_declared_segmented_teeth_suppresses_notice() -> None:
    plan = _plan(
        ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2),
        data=DataAvailability(segmented_teeth=True),
    )
    assert evaluate_segmentation_presence(plan) == []


# --- no movement ---

def test_all_zero_deltas_flag_no_movement() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11")))
    findings = evaluate_no_movement(plan)
    assert len(findings) == 1
    assert findings[0].severity == "info"


def test_nonzero_movement_has_no_no_movement_finding() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1))
    assert evaluate_no_movement(plan) == []


def test_empty_plan_has_no_no_movement_finding() -> None:
    assert evaluate_no_movement(TreatmentPlan(id="empty")) == []
