from __future__ import annotations

from pathlib import Path

from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.io.stl_import import inspect_stl
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.assets import MeshUnits
from orthoplan.model.settings import AxisCaps, MovementCaps, TreatmentSettings
from orthoplan.planning.mesh_frame import compute_local_frame
from orthoplan.viz import build_stage_progress_frames


def _tooth(value: str = "11") -> ToothId:
    return ToothId(value=value)


def _write_ascii_stl(path: Path, triangles: list[tuple[tuple[float, float, float], ...]]) -> None:
    lines = ["solid golden"]
    for tri in triangles:
        lines.extend(
            [
                "  facet normal 0 0 1",
                "    outer loop",
                f"      vertex {tri[0][0]} {tri[0][1]} {tri[0][2]}",
                f"      vertex {tri[1][0]} {tri[1][1]} {tri[1][2]}",
                f"      vertex {tri[2][0]} {tri[2][1]} {tri[2][2]}",
                "    endloop",
                "  endfacet",
            ]
        )
    lines.append("endsolid golden")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_golden_cumulative_translation_is_exact_vector_sum() -> None:
    plan = TreatmentPlan(
        id="golden-translation",
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=_tooth(), translate_x_mm=0.125)]),
            Stage(
                index=1,
                deltas=[
                    ToothDelta(
                        tooth=_tooth(),
                        translate_x_mm=0.375,
                        translate_y_mm=-0.25,
                        translate_z_mm=0.1,
                    )
                ],
            ),
        ],
    )

    frames = build_stage_progress_frames(plan)
    pose = frames[1].poses[0]

    assert pose.translate_x_mm == 0.5
    assert pose.translate_y_mm == -0.25
    assert pose.translate_z_mm == 0.1


def test_golden_horizontal_cap_uses_euclidean_resultant_not_axis_max() -> None:
    plan = TreatmentPlan(
        id="golden-cap",
        settings=TreatmentSettings(
            movement_caps=MovementCaps(default=AxisCaps(linear_mm=0.5, reference="test cap"))
        ),
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=_tooth(), translate_x_mm=0.4, translate_y_mm=0.4)],
            )
        ],
    )

    findings = evaluate_movement_caps(plan)

    assert len(findings) == 1
    assert "0.566 mm" in findings[0].message
    assert "linear cap" in findings[0].title


def test_golden_vertical_and_angular_caps_are_checked_independently() -> None:
    plan = TreatmentPlan(
        id="golden-axis-caps",
        settings=TreatmentSettings(
            movement_caps=MovementCaps(
                default=AxisCaps(
                    linear_mm=1.0,
                    intrusion_extrusion_mm=0.2,
                    angular_deg=2.0,
                    rotation_deg=5.0,
                    reference="test cap",
                )
            )
        ),
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=_tooth(),
                        translate_z_mm=0.25,
                        rotate_tip_deg=2.5,
                        rotate_rotation_deg=6.0,
                    )
                ],
            )
        ],
    )

    titles = [finding.title for finding in evaluate_movement_caps(plan)]

    assert titles == [
        "Stage 0 exceeds configured vertical cap",
        "Stage 0 exceeds configured angular cap",
        "Stage 0 exceeds configured rotation cap",
    ]


def test_golden_stl_fixture_reports_expected_bounds_and_scale(tmp_path: Path) -> None:
    path = tmp_path / "known_bounds.stl"
    _write_ascii_stl(
        path,
        [
            ((0.0, 0.0, 0.0), (12.0, 0.0, 0.0), (0.0, 8.0, 0.0)),
            ((12.0, 0.0, 5.0), (12.0, 8.0, 5.0), (0.0, 8.0, 5.0)),
        ],
    )

    asset = inspect_stl(path)

    assert asset.vertex_count == 6
    assert asset.face_count == 2
    assert asset.units == MeshUnits.UNVERIFIED
    assert asset.bounds is not None
    assert asset.bounds.min_xyz == (0.0, 0.0, 0.0)
    assert asset.bounds.max_xyz == (12.0, 8.0, 5.0)
    assert asset.bounds.max_span == 12.0


def test_golden_pca_frame_matches_known_principal_direction_with_tolerance() -> None:
    vertices = [(x, 0.05 * x, 0.0) for x in (-5, -3, -1, 1, 3, 5)]
    vertices += [(0.0, 0.8, 0.0), (0.0, -0.8, 0.0), (0.0, 0.0, 0.2)]

    frame = compute_local_frame(vertices)

    assert frame is not None
    axis = frame.axes[0]
    dot = abs(axis[0] * 1.0 + axis[1] * 0.05) / (1.0 + 0.05**2) ** 0.5
    assert dot > 0.98
