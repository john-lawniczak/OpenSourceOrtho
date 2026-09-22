from __future__ import annotations

from orthoplan.evaluation.rules import evaluate_movement_caps
import pytest

from orthoplan.model import (
    AxisCaps,
    MeshAsset,
    MeshUnits,
    MovementCaps,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)


def _plan(delta: ToothDelta, **plan_kwargs: object) -> TreatmentPlan:
    return TreatmentPlan(id="caps-test", stages=[Stage(index=0, deltas=[delta])], **plan_kwargs)


def test_flags_excess_single_axis_movement() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.30))
    findings = evaluate_movement_caps(plan)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].code == "movement-cap-exceeded"
    assert findings[0].data_gap
    assert findings[0].clinician_question


def test_allows_movement_within_cap() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.20))
    assert evaluate_movement_caps(plan) == []


def test_diagonal_movement_uses_euclidean_magnitude() -> None:
    # Each axis is 0.18 (< 0.25) but the resultant is ~0.255 (> 0.25).
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.18, translate_y_mm=0.18))
    findings = evaluate_movement_caps(plan)
    assert len(findings) == 1
    assert "linear cap" in findings[0].title


def test_vertical_cap_is_separate_from_horizontal() -> None:
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_z_mm=0.20))
    findings = evaluate_movement_caps(plan)
    assert len(findings) == 1
    assert "vertical cap" in findings[0].title


def test_cap_evaluation_is_gated_on_confirmed_scale() -> None:
    unverified = UploadedScan(
        asset=MeshAsset(id="a", format="stl-binary", vertex_count=0, face_count=0)
    )
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=5.0), scans=[unverified])
    findings = evaluate_movement_caps(plan)
    assert len(findings) == 1
    assert findings[0].code == "movement-cap-scale-unconfirmed"
    assert "units unverified" in findings[0].title

    confirmed = UploadedScan(
        asset=MeshAsset(
            id="a", format="stl-binary", vertex_count=0, face_count=0, units=MeshUnits.MM
        )
    )
    plan_ok = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=5.0), scans=[confirmed])
    findings_ok = evaluate_movement_caps(plan_ok)
    assert any("linear cap" in f.title for f in findings_ok)


def test_movement_cap_override_keys_must_be_canonical_fdi() -> None:
    with pytest.raises(ValueError, match="canonical FDI"):
        MovementCaps(per_tooth_overrides={"UR1": AxisCaps(linear_mm=0.1)})


def test_movement_cap_override_is_used() -> None:
    settings = TreatmentSettings(
        movement_caps=MovementCaps(per_tooth_overrides={"11": AxisCaps(linear_mm=0.1)})
    )
    plan = _plan(ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2), settings=settings)

    findings = evaluate_movement_caps(plan)

    assert len(findings) == 1
    assert "0.1 mm" in findings[0].message
