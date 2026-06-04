from __future__ import annotations

import pytest

from orthoplan.model import (
    MeshAsset,
    MeshUnits,
    PrintExportSettings,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)
from orthoplan.printing import build_print_export_status


def _plan(settings: TreatmentSettings) -> TreatmentPlan:
    scan = UploadedScan(
        asset=MeshAsset(
            id="scan",
            format="stl-binary",
            units=MeshUnits.MM,
            vertex_count=3,
            face_count=1,
        )
    )
    return TreatmentPlan(
        id="print-plan",
        data={"segmented_teeth": True},
        settings=settings,
        scans=[scan],
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)])
        ],
    )


def test_print_export_status_lists_blockers_by_default() -> None:
    status = build_print_export_status(TreatmentPlan(id="blocked"))
    assert status.ready is False
    assert "print export is disabled" in status.blockers
    assert "no staged plan exists to export" in status.blockers


def test_print_export_status_becomes_ready_with_confirmed_inputs() -> None:
    settings = TreatmentSettings(
        print_export=PrintExportSettings(
            enabled=True,
            safety_acknowledged=True,
            delivery_email="user@example.com",
        )
    )

    status = build_print_export_status(_plan(settings))

    assert status.ready is True
    assert status.delivery_email == "user@example.com"
    assert status.artifacts[0].filename == "print-plan-stage-00-model.stl"
    assert "clinician-supervised" in status.caveat


def test_print_export_email_validation_is_basic_but_enforced() -> None:
    with pytest.raises(ValueError, match="email"):
        PrintExportSettings(delivery_email="not-an-address")
