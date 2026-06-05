from __future__ import annotations

from pathlib import Path

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
from orthoplan.validation.measurement_models import (
    MeasurementTruthResult,
    MeasurementValue,
    close,
    result,
)

FIXTURE_DIR = Path(__file__).parent / "golden_fixtures"


def golden_stl_bounds() -> MeasurementTruthResult:
    case_id = "golden-stl-bounds"
    expected: dict[str, MeasurementValue] = {
        "face_count": 2,
        "vertex_count": 6,
        "min_x_mm": -2.0,
        "min_y_mm": 0.0,
        "min_z_mm": 0.0,
        "max_x_mm": 12.0,
        "max_y_mm": 8.0,
        "max_z_mm": 3.0,
        "max_span_mm": 14.0,
    }
    tolerances = {key: 1e-9 for key in expected if key.endswith("_mm")}
    asset = inspect_stl(FIXTURE_DIR / "golden_bounds_ascii.stl")
    observed: dict[str, MeasurementValue] = {
        "face_count": asset.face_count,
        "vertex_count": asset.vertex_count,
    }
    failures: list[str] = []
    if asset.bounds is None:
        failures.append("missing bounds")
    else:
        observed.update(
            {
                "min_x_mm": asset.bounds.min_xyz[0],
                "min_y_mm": asset.bounds.min_xyz[1],
                "min_z_mm": asset.bounds.min_xyz[2],
                "max_x_mm": asset.bounds.max_xyz[0],
                "max_y_mm": asset.bounds.max_xyz[1],
                "max_z_mm": asset.bounds.max_xyz[2],
                "max_span_mm": asset.bounds.max_span,
            }
        )
    _compare_expected(expected, observed, tolerances, failures)
    return result(case_id, failures, expected=expected, observed=observed, tolerances=tolerances)


def golden_stl_degenerate() -> MeasurementTruthResult:
    case_id = "golden-stl-degenerate"
    asset = inspect_stl(FIXTURE_DIR / "golden_degenerate_ascii.stl")
    expected: dict[str, MeasurementValue] = {"degenerate_faces": 1}
    observed: dict[str, MeasurementValue] = {
        "degenerate_faces": asset.quality.degenerate_faces,
    }
    failures = (
        []
        if asset.quality.degenerate_faces == 1
        else [f"degenerate_faces: expected 1, got {asset.quality.degenerate_faces}"]
    )
    return result(case_id, failures, expected=expected, observed=observed)


def bounds_known_ascii() -> MeasurementTruthResult:
    case_id = "bounds-known-ascii"
    failures: list[str] = []
    asset = inspect_stl(FIXTURE_DIR / "golden_bounds_ascii.stl")
    if asset.bounds is None:
        failures.append("missing bounds")
    else:
        close(asset.bounds.max_xyz[0], 12.0, 1e-9, "max x", failures)
        close(asset.bounds.max_xyz[1], 8.0, 1e-9, "max y", failures)
        close(asset.bounds.max_span, 14.0, 1e-9, "max span", failures)
    if asset.face_count != 2:
        failures.append(f"face count: expected 2, got {asset.face_count}")
    return result(case_id, failures)


def cumulative_translation() -> MeasurementTruthResult:
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
    close(pose["translate_x_mm"], 0.5, 1e-9, "x", failures)
    close(pose["translate_y_mm"], -0.1, 1e-9, "y", failures)
    close(pose["translate_z_mm"], 0.05, 1e-9, "z", failures)
    expected = {"x_mm": 0.5, "y_mm": -0.1, "z_mm": 0.05}
    observed = {
        "x_mm": pose["translate_x_mm"],
        "y_mm": pose["translate_y_mm"],
        "z_mm": pose["translate_z_mm"],
    }
    return result(case_id, failures, expected=expected, observed=observed)


def known_mm_degree_transform() -> MeasurementTruthResult:
    case_id = "known-mm-degree-transform"
    plan = TreatmentPlan(
        id=case_id,
        stages=[
            Stage(index=0, deltas=[_delta(1.25, -0.75, 0.40, 2.5, -1.25, 3.75)]),
            Stage(index=1, deltas=[_delta(-0.25, 0.10, 0.05, 0.5, -0.75, 1.25)]),
        ],
    )
    pose = evaluate_plan(plan)["frames"][1]["poses"][0]
    expected: dict[str, MeasurementValue] = {
        "translate_x_mm": 1.0,
        "translate_y_mm": -0.65,
        "translate_z_mm": 0.45,
        "rotate_tip_deg": 3.0,
        "rotate_torque_deg": -2.0,
        "rotate_rotation_deg": 5.0,
        "rotation_renderable": False,
    }
    observed = {key: pose[key] for key in expected}
    failures: list[str] = []
    _compare_expected(expected, observed, {}, failures)
    tolerances = {key: 1e-9 for key in expected if key.endswith(("_mm", "_deg"))}
    return result(case_id, failures, expected=expected, observed=observed, tolerances=tolerances)


def rotation_gating() -> MeasurementTruthResult:
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
    return result(case_id, failures)


def movement_cap_resultant() -> MeasurementTruthResult:
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
    return result(case_id, failures)


def segmentation_linkage() -> MeasurementTruthResult:
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
        return result(case_id, failures)
    failures.append("wrong-tooth mesh reference was accepted")
    return result(case_id, failures)


def report_reproducibility() -> MeasurementTruthResult:
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
    return result(case_id, failures)


def _delta(x: float, y: float, z: float, tip: float, torque: float, rotation: float) -> ToothDelta:
    return ToothDelta(
        tooth=ToothId(value="11"),
        translate_x_mm=x,
        translate_y_mm=y,
        translate_z_mm=z,
        rotate_tip_deg=tip,
        rotate_torque_deg=torque,
        rotate_rotation_deg=rotation,
    )


def _compare_expected(
    expected: dict[str, MeasurementValue],
    observed: dict[str, MeasurementValue],
    tolerances: dict[str, float],
    failures: list[str],
) -> None:
    for key, expected_value in expected.items():
        actual = observed.get(key)
        if isinstance(expected_value, float) and isinstance(actual, float):
            close(actual, expected_value, tolerances.get(key, 1e-9), key, failures)
        elif actual != expected_value:
            failures.append(f"{key}: expected {expected_value}, got {actual}")
