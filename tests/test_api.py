from __future__ import annotations

from orthoplan.api import evaluate_plan, evaluate_plan_payload
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


def test_tooth_frames_exposed_for_3d_viewer() -> None:
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
    assert result["frames"][0]["poses"][0]["rotation_renderable"] is True


def test_tooth_frames_empty_without_local_frames() -> None:
    result = evaluate_plan_payload(_base_payload())
    assert result["tooth_frames"] == {}


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
