from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from orthoplan.model import (
    BoundingBox,
    MeshAsset,
    MeshUnits,
    PrintExportSettings,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)
from orthoplan.printing import build_print_export_status
from orthoplan.printing import export_print_package


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


def _segmented_plan(settings: TreatmentSettings) -> TreatmentPlan:
    asset = MeshAsset(
        id="tooth-11",
        format="stl-ascii",
        units=MeshUnits.MM,
        vertex_count=8,
        face_count=12,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(4.0, 5.0, 6.0)),
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        inspected_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )
    return TreatmentPlan(
        id="segmented-print",
        data={"segmented_teeth": True},
        settings=settings,
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="tooth-11")
        ],
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
    assert "user's own responsibility" in status.caveat


def test_print_export_email_validation_is_basic_but_enforced() -> None:
    with pytest.raises(ValueError, match="email"):
        PrintExportSettings(delivery_email="not-an-address")


def test_export_print_package_writes_stl_manifest_zip_and_email(tmp_path) -> None:
    settings = TreatmentSettings(
        print_export=PrintExportSettings(
            enabled=True,
            safety_acknowledged=True,
            delivery_email="user@example.com",
        )
    )

    result = export_print_package(
        _plan(settings),
        tmp_path,
        make_zip=True,
        make_email_draft=True,
    )

    assert result.artifact_paths
    assert result.artifact_paths[0].endswith(".stl")
    assert "facet normal" in Path(result.artifact_paths[0]).read_text(encoding="utf-8")
    assert len(result.artifact_sha256[Path(result.artifact_paths[0]).name]) == 64
    assert len(result.manifest_sha256) == 64
    assert result.zip_path and Path(result.zip_path).is_file()
    assert result.zip_sha256 and len(result.zip_sha256) == 64
    assert result.email_draft_path and Path(result.email_draft_path).is_file()


def test_export_print_package_manifest_binds_hashes_and_geometry_sources(tmp_path) -> None:
    settings = TreatmentSettings(
        print_export=PrintExportSettings(enabled=True, safety_acknowledged=True)
    )

    result = export_print_package(_segmented_plan(settings), tmp_path, make_zip=True)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert manifest["schema"] == "orthoplan-print-package-v1"
    assert len(manifest["plan_sha256"]) == 64
    assert len(manifest["stage_frames_sha256"]) == 64
    artifact = manifest["artifacts"][0]
    assert artifact["sha256"] == result.artifact_sha256[artifact["filename"]]
    source = artifact["geometry_sources"][0]
    assert source["source"] == "segmented-mesh-bounds:tooth-11"
    assert source["size_xyz_mm"] == [4.0, 5.0, 6.0]

    repeated = export_print_package(_segmented_plan(settings), tmp_path / "again", make_zip=True)
    assert result.artifact_sha256 == repeated.artifact_sha256
    assert result.zip_sha256 == repeated.zip_sha256


def test_export_print_package_neutralizes_traversal_in_plan_id(tmp_path) -> None:
    settings = TreatmentSettings(
        print_export=PrintExportSettings(enabled=True, safety_acknowledged=True)
    )
    plan = _plan(settings).model_copy(update={"id": "../../evil"})

    result = export_print_package(plan, tmp_path, make_zip=True, make_email_draft=True)

    written = [Path(result.manifest_path), *[Path(p) for p in result.artifact_paths]]
    if result.zip_path:
        written.append(Path(result.zip_path))
    if result.email_draft_path:
        written.append(Path(result.email_draft_path))
    for path in written:
        resolved = path.resolve()
        assert resolved.is_relative_to(tmp_path.resolve()), resolved
        assert ".." not in path.name
