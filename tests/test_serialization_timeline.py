from __future__ import annotations

from pathlib import Path

from orthoplan.io.serialization import plan_from_json, plan_to_json, read_plan, write_plan
from orthoplan.model import (
    MeshAsset,
    MeshUnits,
    Stage,
    TimelineSettings,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)
from orthoplan.planning.timeline import PROJECTION_CAVEAT, project_timeline


def _rich_plan() -> TreatmentPlan:
    scan = UploadedScan(
        asset=MeshAsset(
            id="a", format="stl-binary", vertex_count=3, face_count=1, units=MeshUnits.MM
        )
    )
    return TreatmentPlan(
        id="rt",
        title="Round trip",
        settings=TreatmentSettings(timeline=TimelineSettings(wear_interval_days=10)),
        scans=[scan],
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)]),
            Stage(index=1, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_z_mm=0.05)]),
        ],
    )


def test_plan_json_round_trips_losslessly() -> None:
    plan = _rich_plan()
    assert plan_from_json(plan_to_json(plan)) == plan


def test_plan_file_round_trips(tmp_path: Path) -> None:
    plan = _rich_plan()
    path = tmp_path / "plan.json"
    write_plan(plan, path)
    assert read_plan(path) == plan


def test_timeline_is_arithmetic_with_caveat() -> None:
    plan = _rich_plan()
    projection = project_timeline(plan)
    assert projection.stage_count == 2
    assert projection.wear_interval_days == 10
    assert projection.projected_duration_days == 20
    assert projection.caveat == PROJECTION_CAVEAT
