"""Measurement Truth Lab.

Built-in synthetic cases exercise the public engine path and compare outputs
against known measurements with explicit tolerances. Fixtures are generated in
memory or temporary files and contain no patient data.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, Field

from orthoplan.api import evaluate_plan
from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.io.stl_import import inspect_stl
from orthoplan.model import (
    MeshAsset,
    MeshUnits,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    ToothLocalFrame,
    TreatmentPlan,
)
from orthoplan.reporting import build_handoff_report, plan_digest


class MeasurementTruthResult(BaseModel):
    case_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)


CaseFn = Callable[[], MeasurementTruthResult]


def run_measurement_lab(case_id: str | None = None) -> list[MeasurementTruthResult]:
    cases: dict[str, CaseFn] = {
        "bounds-known-ascii": _case_bounds_known_ascii,
        "cumulative-translation": _case_cumulative_translation,
        "rotation-gating": _case_rotation_gating,
        "movement-cap-resultant": _case_movement_cap_resultant,
        "segmentation-linkage": _case_segmentation_linkage,
        "report-reproducibility": _case_report_reproducibility,
    }
    selected = {case_id: cases[case_id]} if case_id else cases
    return [fn() for fn in selected.values()]


def _result(case_id: str, failures: list[str]) -> MeasurementTruthResult:
    return MeasurementTruthResult(case_id=case_id, passed=not failures, failures=failures)


def _close(
    actual: float,
    expected: float,
    tolerance: float,
    label: str,
    failures: list[str],
) -> None:
    if abs(actual - expected) > tolerance:
        failures.append(f"{label}: expected {expected}, got {actual}")


def _case_bounds_known_ascii() -> MeasurementTruthResult:
    case_id = "bounds-known-ascii"
    failures: list[str] = []
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "known.stl"
        path.write_text(
            "\n".join(
                [
                    "solid known",
                    "facet normal 0 0 1",
                    "outer loop",
                    "vertex 0 0 0",
                    "vertex 12 0 0",
                    "vertex 0 8 0",
                    "endloop",
                    "endfacet",
                    "endsolid known",
                ]
            ),
            encoding="utf-8",
        )
        asset = inspect_stl(path)
    if asset.bounds is None:
        failures.append("missing bounds")
    else:
        _close(asset.bounds.max_xyz[0], 12.0, 1e-9, "max x", failures)
        _close(asset.bounds.max_xyz[1], 8.0, 1e-9, "max y", failures)
        _close(asset.bounds.max_span, 12.0, 1e-9, "max span", failures)
    if asset.face_count != 1:
        failures.append(f"face count: expected 1, got {asset.face_count}")
    return _result(case_id, failures)


def _case_cumulative_translation() -> MeasurementTruthResult:
    case_id = "cumulative-translation"
    plan = TreatmentPlan(
        id=case_id,
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)]),
            Stage(
                index=1,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        translate_x_mm=0.3,
                        translate_y_mm=-0.1,
                        translate_z_mm=0.05,
                    )
                ],
            ),
        ],
    )
    pose = evaluate_plan(plan)["frames"][1]["poses"][0]
    failures: list[str] = []
    _close(pose["translate_x_mm"], 0.5, 1e-9, "x", failures)
    _close(pose["translate_y_mm"], -0.1, 1e-9, "y", failures)
    _close(pose["translate_z_mm"], 0.05, 1e-9, "z", failures)
    return _result(case_id, failures)


def _case_rotation_gating() -> MeasurementTruthResult:
    case_id = "rotation-gating"
    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    approximate = TreatmentPlan(
        id=case_id,
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="m11",
                local_frame=ToothLocalFrame(
                    origin=(0, 0, 0), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))
                ),
            )
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"))])],
    )
    trusted = approximate.model_copy(
        update={
            "tooth_meshes": [
                approximate.tooth_meshes[0].model_copy(
                    update={
                        "local_frame": approximate.tooth_meshes[0].local_frame.model_copy(
                            update={"approximate": False}
                        )
                    }
                )
            ]
        }
    )
    failures: list[str] = []
    if evaluate_plan(approximate)["frames"][0]["rotation_renderable"]:
        failures.append("approximate PCA frame made rotation renderable")
    if not evaluate_plan(trusted)["frames"][0]["rotation_renderable"]:
        failures.append("trusted frame did not make rotation renderable")
    return _result(case_id, failures)


def _case_movement_cap_resultant() -> MeasurementTruthResult:
    case_id = "movement-cap-resultant"
    plan = TreatmentPlan(
        id=case_id,
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.18, translate_y_mm=0.18)
                ],
            )
        ],
    )
    findings = evaluate_movement_caps(plan)
    failures = [] if any("linear cap" in finding.title for finding in findings) else ["missing cap"]
    return _result(case_id, failures)


def _case_segmentation_linkage() -> MeasurementTruthResult:
    case_id = "segmentation-linkage"
    failures: list[str] = []
    asset = MeshAsset(
        id="m11",
        format="stl-binary",
        units=MeshUnits.MM,
        vertex_count=3,
        face_count=1,
    )
    try:
        TreatmentPlan(
            id=case_id,
            mesh_assets=[asset],
            tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="m11")],
            stages=[
                Stage(
                    index=0,
                    deltas=[ToothDelta(tooth=ToothId(value="21"), mesh_asset_id="m11")],
                )
            ],
        )
    except ValueError:
        return _result(case_id, failures)
    failures.append("wrong-tooth mesh reference was accepted")
    return _result(case_id, failures)


def _case_report_reproducibility() -> MeasurementTruthResult:
    case_id = "report-reproducibility"
    plan = TreatmentPlan(
        id=case_id,
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )
    report_a = build_handoff_report(plan)
    report_b = build_handoff_report(plan)
    failures: list[str] = []
    if plan_digest(plan) != plan_digest(plan):
        failures.append("plan digest unstable")
    if report_a["evaluation_sha256"] != report_b["evaluation_sha256"]:
        failures.append("evaluation digest unstable")
    return _result(case_id, failures)
