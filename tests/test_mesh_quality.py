from __future__ import annotations

from orthoplan.evaluation.engine import run_rules
from orthoplan.evaluation.rules import evaluate_mesh_quality
from orthoplan.model import (
    MeshAsset,
    MeshProvenance,
    MeshUnits,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.model.assets import BoundingBox, MeshQualityReport, UploadedScan


def _asset(**overrides: object) -> MeshAsset:
    base = dict(id="mesh-1", format="stl-binary", vertex_count=3, face_count=1)
    base.update(overrides)
    return MeshAsset(**base)  # type: ignore[arg-type]


def test_degenerate_faces_become_a_finding() -> None:
    asset = _asset(quality=MeshQualityReport(degenerate_faces=2))
    plan = TreatmentPlan(id="p", mesh_assets=[asset])
    findings = evaluate_mesh_quality(plan)
    assert any("degenerate triangles" in f.title for f in findings)
    assert all(f.severity == "notice" for f in findings)


def test_non_watertight_becomes_a_finding() -> None:
    asset = _asset(quality=MeshQualityReport(watertight=False))
    findings = evaluate_mesh_quality(TreatmentPlan(id="p", mesh_assets=[asset]))
    assert any("not watertight" in f.title for f in findings)


def test_no_quality_report_produces_no_findings() -> None:
    asset = _asset()
    assert evaluate_mesh_quality(TreatmentPlan(id="p", mesh_assets=[asset])) == []


def test_confirmed_implausible_scale_is_flagged_once() -> None:
    # 5 mm span with confirmed mm units is far below the 30-120 mm arch range.
    asset = _asset(
        units=MeshUnits.MM,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(5, 4, 3)),
        provenance=MeshProvenance.IMPORTED,
    )
    findings = evaluate_mesh_quality(TreatmentPlan(id="p", mesh_assets=[asset]))
    scale = [f for f in findings if "scale looks implausible" in f.title]
    assert len(scale) == 1


def test_run_rules_combines_caps_and_mesh_quality() -> None:
    scan = UploadedScan(asset=_asset(id="scan-1", units=MeshUnits.MM, quality=MeshQualityReport(watertight=False)))
    plan = TreatmentPlan(
        id="p",
        scans=[scan],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.5)])],
    )
    findings = run_rules(plan)
    titles = [f.title for f in findings]
    assert any("linear cap" in t for t in titles)  # movement-cap rule
    assert any("not watertight" in t for t in titles)  # mesh-quality rule
