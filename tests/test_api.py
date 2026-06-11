from __future__ import annotations

import base64

from orthoplan.api import evaluate_plan, evaluate_plan_payload, print_package_payload
from orthoplan.model import (
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    ToothLocalFrame,
    TreatmentPlan,
)


def _base_payload(**overrides: object) -> dict:
    payload = {
        "id": "ui-plan",
        "title": "UI plan",
        "numbering_system": "FDI",
        "coordinate_frame": {"name": "scan-local"},
        "settings": {"timeline": {"wear_interval_days": 14}},
        "stages": [
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]},
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_payload_returns_engine_output() -> None:
    result = evaluate_plan_payload(_base_payload())
    assert result["ok"] is True
    assert result["scale_confirmed"] is True
    assert "roots unavailable" in result["data_gaps"]
    assert result["timeline"]["projected_duration_days"] == 14
    assert len(result["frames"]) == 1
    pose = result["frames"][0]["poses"][0]
    assert pose["tooth"] == "11"
    assert pose["translate_x_mm"] == 0.2
    assert result["frames"][0]["rotation_renderable"] is False


def test_findings_carry_safety_fields() -> None:
    payload = _base_payload(
        stages=[
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.5}]},
        ]
    )
    result = evaluate_plan_payload(payload)
    assert result["findings"], "expected a cap finding"
    finding = result["findings"][0]
    # The engine output carries the mandated safety context the bare-string UI lacked.
    assert finding["severity"] == "warning"
    assert finding["code"] == "movement-cap-exceeded"
    assert finding["data_gap"]
    assert finding["clinician_question"]


def test_invalid_fdi_is_returned_as_errors_not_raised() -> None:
    payload = _base_payload(
        stages=[{"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "99"}}]}]
    )
    result = evaluate_plan_payload(payload)
    assert result["ok"] is False
    assert any("99" in message or "FDI" in message for message in result["errors"])


def test_non_contiguous_stages_are_rejected_as_errors() -> None:
    payload = _base_payload(
        stages=[{"index": 0, "deltas": []}, {"index": 2, "deltas": []}]
    )
    result = evaluate_plan_payload(payload)
    assert result["ok"] is False
    assert any("contiguous" in message for message in result["errors"])


def test_approximate_tooth_frames_are_exposed_but_do_not_render_rotation() -> None:
    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    plan = TreatmentPlan(
        id="rot",
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
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="m11")])],
    )
    result = evaluate_plan(plan)
    assert "11" in result["tooth_frames"]
    assert result["tooth_frames"]["11"]["approximate"] is True
    assert result["frames"][0]["poses"][0]["rotation_renderable"] is False


def test_trusted_tooth_frame_allows_rotation_rendering() -> None:
    asset = MeshAsset(id="m11", format="stl-binary", vertex_count=3, face_count=1)
    plan = TreatmentPlan(
        id="rot",
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="m11",
                local_frame=ToothLocalFrame(
                    origin=(0, 0, 0),
                    axes=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                    source="trusted-anatomical-frame",
                    approximate=False,
                ),
            )
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="m11")])],
    )

    result = evaluate_plan(plan)

    assert result["tooth_frames"]["11"]["approximate"] is False
    assert result["frames"][0]["poses"][0]["rotation_renderable"] is True


def test_tooth_frames_empty_without_local_frames() -> None:
    result = evaluate_plan_payload(_base_payload())
    assert result["tooth_frames"] == {}


def test_data_gap_actions_explain_limited_capabilities() -> None:
    result = evaluate_plan_payload(_base_payload())
    assert result["data_gap_actions"]
    root_action = next(action for action in result["data_gap_actions"] if action["gap"] == "roots unavailable")
    assert "Root position" in root_action["impact"]
    assert "root movement assessment" in root_action["blocked_capabilities"]


def test_acquisition_advice_is_included_in_engine_output() -> None:
    result = evaluate_plan_payload(_base_payload())
    advice = result["acquisition_advice"]
    assert advice["baseline_finding_count"] == len(result["findings"])
    assert advice["baseline_data_gaps"] == result["data_gaps"]
    assert advice["impacts"]
    assert any(impact["modality"] == "roots" for impact in advice["impacts"])


def test_print_export_status_is_included_in_engine_output() -> None:
    result = evaluate_plan_payload(_base_payload())
    status = result["print_export"]
    assert status["enabled"] is False
    assert status["ready"] is False
    assert "print export is disabled" in status["blockers"]
    assert status["manufacturing_readiness"]["verdict"] == "NOT_APPLICABLE"
    assert "user's own responsibility" in status["caveat"]


def test_unverified_scan_units_gate_cap_evaluation() -> None:
    payload = _base_payload(
        scans=[{"asset": {"id": "a", "format": "stl", "vertex_count": 0, "face_count": 0}}],
        stages=[
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 5.0}]},
        ],
    )
    result = evaluate_plan_payload(payload)
    assert result["ok"] is True
    assert result["scale_confirmed"] is False
    assert any("units unverified" in f["title"] for f in result["findings"])


def test_render_mesh_links_are_included_for_tooth_meshes() -> None:
    plan = TreatmentPlan(
        id="render",
        mesh_assets=[MeshAsset(id="mesh-11", format="stl-ascii", vertex_count=3, face_count=1)],
        tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
            )
        ],
    )

    result = evaluate_plan(plan)

    assert result["render_meshes"] == [
        {"tooth": "11", "mesh_asset_id": "mesh-11", "url": "/api/mesh/mesh-11", "source": "manual"}
    ]


def _ready_print_payload() -> dict:
    payload = _base_payload(
        scans=[
            {
                "asset": {
                    "id": "scan",
                    "format": "stl",
                    "units": "mm",
                    "vertex_count": 0,
                    "face_count": 0,
                }
            }
        ],
        data={"segmented_teeth": True},
        settings={
            "timeline": {"wear_interval_days": 14},
            "print_export": {"enabled": True, "safety_acknowledged": True},
        },
    )
    return payload


def test_print_package_payload_returns_downloadable_zip_when_ready() -> None:
    result = print_package_payload(_ready_print_payload())

    assert result["ok"] is True
    assert result["stage_count"] == 1
    zip_bytes = base64.b64decode(result["zip_base64"])
    assert zip_bytes[:2] == b"PK"  # zip local-file-header magic
    eml_bytes = base64.b64decode(result["email_eml_base64"])
    assert b"OpenSource Ortho print package" in eml_bytes
    assert result["email_filename"].endswith(".eml")
    assert result["filename"].endswith(".zip")


def test_print_package_payload_returns_blockers_when_not_ready() -> None:
    result = print_package_payload(_base_payload())

    assert result["ok"] is False
    assert "print export is disabled" in result["errors"]
    assert result["print_export"]["ready"] is False
    assert "zip_base64" not in result


def test_print_package_payload_rejects_invalid_plan() -> None:
    payload = _base_payload(
        stages=[{"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "99"}}]}]
    )
    result = print_package_payload(payload)

    assert result["ok"] is False
    assert result["errors"]
