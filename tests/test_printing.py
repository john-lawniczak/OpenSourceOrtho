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
    assert status.manufacturing_readiness["verdict"] == "NOT_APPLICABLE"
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


def test_solid_stl_writes_real_unit_facet_normals() -> None:
    from orthoplan.print_stl import solid_stl

    # A single triangle in the z=0 plane wound counter-clockwise: its outward
    # normal must be exactly +z, not the placeholder 0 0 0 the export used before.
    triangle = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    text = solid_stl("one", [triangle])

    assert "facet normal 0.000000 0.000000 1.000000" in text
    assert "facet normal 0 0 0" not in text


def test_solid_stl_emits_zero_normal_only_for_degenerate_facets() -> None:
    from orthoplan.print_stl import solid_stl

    degenerate = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    text = solid_stl("deg", [degenerate])

    assert "facet normal 0.000000 0.000000 0.000000" in text


def test_export_print_package_manifest_binds_hashes_and_geometry_sources(tmp_path) -> None:
    settings = TreatmentSettings(
        print_export=PrintExportSettings(enabled=True, safety_acknowledged=True)
    )

    result = export_print_package(_segmented_plan(settings), tmp_path, make_zip=True)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert manifest["schema"] == "orthoplan-print-package-v2"
    assert len(manifest["hashes"]["plan_sha256"]) == 64
    assert len(manifest["hashes"]["stage_frames_sha256"]) == 64
    assert len(manifest["hashes"]["findings_sha256"]) == 64
    assert manifest["review_tier"]["tier"] == "stl-only"
    # An unreviewed segmentation link falls closed to a labeled bounds proxy.
    assert manifest["uses_real_mesh_geometry"] is False
    artifact = manifest["artifacts"][0]
    assert artifact["sha256"] == result.artifact_sha256[artifact["filename"]]
    source = artifact["geometry_sources"][0]
    assert source["source"] == "segmented-mesh-bounds:tooth-11"
    assert source["size_xyz_mm"] == [4.0, 5.0, 6.0]

    repeated = export_print_package(_segmented_plan(settings), tmp_path / "again", make_zip=True)
    assert result.artifact_sha256 == repeated.artifact_sha256
    assert result.zip_sha256 == repeated.zip_sha256


_ASCII_STL = """solid frag
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 0 1 0
      vertex 0 0 1
    endloop
  endfacet
endsolid frag
"""


def _ready_settings() -> TreatmentSettings:
    return TreatmentSettings(
        print_export=PrintExportSettings(enabled=True, safety_acknowledged=True)
    )


def _plan_with_fragment(asset, *, reviewed: bool) -> TreatmentPlan:
    return TreatmentPlan(
        id="frag-print",
        data={"segmented_teeth": True},
        settings=_ready_settings(),
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"), mesh_asset_id=asset.id, reviewed=reviewed
            )
        ],
        stages=[
            Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)])
        ],
    )


def test_reviewed_segmentation_exports_real_mesh_vertices(tmp_path) -> None:
    from orthoplan.mesh_workspace import register_stl_mesh

    src = tmp_path / "frag.stl"
    src.write_text(_ASCII_STL, encoding="utf-8")
    workspace = tmp_path / "ws"
    asset = register_stl_mesh(src, workspace=workspace)

    result = export_print_package(
        _plan_with_fragment(asset, reviewed=True), tmp_path / "out", workspace=workspace
    )
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.uses_real_mesh_geometry is True
    assert manifest["uses_real_mesh_geometry"] is True
    assert asset.id in manifest["hashes"]["segmentation_fragment_sha256"]
    source = manifest["artifacts"][0]["geometry_sources"][0]
    assert source["mode"] == "mesh-vertices"
    assert source["source"] == f"segmented-mesh-vertices:{asset.id}"


def test_unreviewed_link_fails_closed_to_proxy_even_with_resolvable_geometry(tmp_path) -> None:
    from orthoplan.mesh_workspace import register_stl_mesh

    src = tmp_path / "frag.stl"
    src.write_text(_ASCII_STL, encoding="utf-8")
    workspace = tmp_path / "ws"
    asset = register_stl_mesh(src, workspace=workspace)

    result = export_print_package(
        _plan_with_fragment(asset, reviewed=False), tmp_path / "out", workspace=workspace
    )

    assert result.uses_real_mesh_geometry is False


def test_reviewed_link_without_resolvable_geometry_fails_closed(tmp_path) -> None:
    # Reviewed, but the fragment was never registered in this workspace: the
    # export must not invent geometry - it falls back to the labeled proxy.
    asset = MeshAsset(
        id="abc123def456",
        format="stl-ascii",
        units=MeshUnits.MM,
        vertex_count=6,
        face_count=2,
        bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(2.0, 3.0, 1.0)),
    )
    result = export_print_package(
        _plan_with_fragment(asset, reviewed=True), tmp_path / "out", workspace=tmp_path / "empty-ws"
    )

    assert result.uses_real_mesh_geometry is False


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
