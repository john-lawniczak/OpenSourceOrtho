"""Fail-closed numeric registration quality gate (Step 1 of the CBCT path)."""

from __future__ import annotations

from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.model.registration_gate import (
    RegistrationGateVerdict,
    best_gated_registration,
    gate_registration,
    gate_registrations,
)
from orthoplan.model.review_tier import accepted_registration


def _reg(reg_id: str = "r1", *, accepted: bool = True, quality: RegistrationQuality | None = None):
    return RegistrationTransform(
        id=reg_id, source_stl_asset_id="scan", target_cbct_record_id="cb",
        accepted=accepted, quality=quality,
    )


def _plan(registrations: list[RegistrationTransform]) -> TreatmentPlan:
    scan = UploadedScan(
        asset=MeshAsset(id="scan", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )
    return TreatmentPlan(
        id="p", scans=[scan],
        case_records=[CaseRecord(id="cb", kind="cbct", local_reference="r/cb.dcm")],
        registrations=registrations,
    )


def _quality(**kwargs) -> RegistrationQuality:
    return RegistrationQuality(method="test", **kwargs)


def test_good_metrics_pass() -> None:
    result = gate_registration(_reg(quality=_quality(rmse_mm=0.2, fitness=0.9)))
    assert result.verdict is RegistrationGateVerdict.PASS
    assert result.open


def test_marginal_metric_downgrades_to_marginal() -> None:
    result = gate_registration(_reg(quality=_quality(rmse_mm=0.8, fitness=0.9)))
    assert result.verdict is RegistrationGateVerdict.MARGINAL
    assert result.open


def test_bad_rmse_fails_even_with_good_fitness() -> None:
    result = gate_registration(_reg(quality=_quality(rmse_mm=5.0, fitness=0.95)))
    assert result.verdict is RegistrationGateVerdict.FAIL
    assert not result.open
    assert any("rmse" in reason for reason in result.reasons)


def test_low_inlier_ratio_fails() -> None:
    result = gate_registration(_reg(quality=_quality(rmse_mm=0.2, inlier_ratio=0.2)))
    assert result.verdict is RegistrationGateVerdict.FAIL


def test_unaccepted_registration_fails_closed() -> None:
    result = gate_registration(_reg(accepted=False, quality=_quality(rmse_mm=0.1)))
    assert result.verdict is RegistrationGateVerdict.FAIL
    assert "not accepted" in result.reasons[0]


def test_missing_quality_fails_closed() -> None:
    result = gate_registration(_reg(quality=None))
    assert result.verdict is RegistrationGateVerdict.FAIL


def test_quality_without_usable_values_fails_closed() -> None:
    result = gate_registration(_reg(quality=_quality()))
    assert result.verdict is RegistrationGateVerdict.FAIL
    assert "no usable values" in result.reasons[0]


def test_best_gated_registration_prefers_pass_over_marginal() -> None:
    plan = _plan([
        _reg("marginal", quality=_quality(rmse_mm=0.9)),
        _reg("pass", quality=_quality(rmse_mm=0.2)),
    ])
    registration, result = best_gated_registration(plan)
    assert registration is not None and registration.id == "pass"
    assert result is not None and result.verdict is RegistrationGateVerdict.PASS


def test_best_gated_registration_none_when_all_fail() -> None:
    plan = _plan([_reg(quality=_quality(rmse_mm=9.0))])
    registration, result = best_gated_registration(plan)
    assert registration is None and result is None


def test_accepted_registration_now_requires_gate_to_open() -> None:
    """A reviewer click with contradicting metrics no longer unlocks CBCT behavior."""

    bad = _plan([_reg(quality=_quality(rmse_mm=9.0))])
    good = _plan([_reg(quality=_quality(rmse_mm=0.2))])
    assert accepted_registration(bad) is None
    assert accepted_registration(good) is not None


def test_gate_registrations_reports_every_registration() -> None:
    plan = _plan([_reg("a", quality=_quality(rmse_mm=0.2)), _reg("b", quality=None)])
    results = {result.registration_id: result.verdict for result in gate_registrations(plan)}
    assert results == {
        "a": RegistrationGateVerdict.PASS,
        "b": RegistrationGateVerdict.FAIL,
    }
