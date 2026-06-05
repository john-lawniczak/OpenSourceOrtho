from __future__ import annotations

from orthoplan.evaluation.acquisition import acquisition_advice, applicable_modalities
from orthoplan.evaluation.finding import _VERDICT_RE
from orthoplan.model import (
    MeshAsset,
    MeshUnits,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    UploadedScan,
)


def _moving_plan(**kwargs: object) -> TreatmentPlan:
    return TreatmentPlan(
        id="acq",
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        translate_x_mm=0.4,
                        rotate_tip_deg=2.0,
                    )
                ],
            )
        ],
        **kwargs,
    )


def _impact(plan: TreatmentPlan, modality: str):
    advice = acquisition_advice(plan)
    return next(impact for impact in advice.impacts if impact.modality == modality)


def test_roots_or_cbct_resolve_root_sensitive_warning() -> None:
    plan = _moving_plan()

    roots = _impact(plan, "roots")
    cbct = _impact(plan, "cbct")

    assert any("Root-sensitive movement" in finding.title for finding in roots.resolves)
    assert any("Root-sensitive movement" in finding.title for finding in cbct.resolves)
    assert roots.closes_data_gaps == ["roots unavailable"]
    assert cbct.closes_data_gaps == ["CBCT unavailable"]


def test_scan_unit_confirmation_surfaces_suppressed_cap_findings() -> None:
    scan = UploadedScan(
        asset=MeshAsset(id="scan", format="stl-binary", vertex_count=3, face_count=1)
    )
    plan = _moving_plan(scans=[scan])

    impact = _impact(plan, "scan_units_confirmed")

    assert impact.unlocks_assessment is True
    assert any("linear cap" in finding.title for finding in impact.surfaces)
    assert any("units unverified" in gap for gap in impact.closes_data_gaps)


def test_already_available_modalities_are_not_advised() -> None:
    scan = UploadedScan(
        asset=MeshAsset(
            id="scan", format="stl-binary", vertex_count=3, face_count=1, units=MeshUnits.MM
        )
    )
    plan = _moving_plan(scans=[scan])
    assert "scan_units_confirmed" not in applicable_modalities(plan)


def test_no_dependency_modalities_are_reported_honestly() -> None:
    plan = _moving_plan()
    photos = _impact(plan, "photos")
    radiographs = _impact(plan, "radiographs")

    assert photos.resolves == []
    assert photos.surfaces == []
    assert photos.closes_data_gaps == []
    assert "No current deterministic finding depends" in photos.note
    assert radiographs.priority_score == 0.0


def test_acquisition_advice_is_deterministic() -> None:
    plan = _moving_plan()
    first = acquisition_advice(plan).model_dump()
    second = acquisition_advice(plan).model_dump()
    assert first == second


def test_acquisition_advice_strings_are_verdict_free() -> None:
    advice = acquisition_advice(_moving_plan())
    strings = [advice.caveat, *advice.baseline_data_gaps]
    for impact in advice.impacts:
        strings.extend([impact.modality, impact.label, impact.acquisition, impact.note])
        strings.extend(impact.closes_data_gaps)
        strings.extend(finding.title for finding in impact.resolves)
        strings.extend(finding.title for finding in impact.surfaces)

    assert not [text for text in strings if _VERDICT_RE.search(text)]
