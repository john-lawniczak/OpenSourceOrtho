from __future__ import annotations

import json
from pathlib import Path

import pytest

from orthoplan.mesh_workspace import register_stl_mesh
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
)
from orthoplan.printing import export_print_package


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


def _settings(**overrides) -> TreatmentSettings:
    values = {"enabled": True, "safety_acknowledged": True, "aligner_shell_enabled": True}
    values.update(overrides)
    return TreatmentSettings(print_export=PrintExportSettings(**values))


def _plan_with_fragment(asset, *, reviewed: bool, settings: TreatmentSettings) -> TreatmentPlan:
    return TreatmentPlan(
        id="frag-print",
        data={"segmented_teeth": True},
        settings=settings,
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id=asset.id, reviewed=reviewed)
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)])],
    )


def _registered_asset(tmp_path: Path, text: str = _ASCII_STL):
    src = tmp_path / "frag.stl"
    src.write_text(text, encoding="utf-8")
    workspace = tmp_path / "ws"
    return register_stl_mesh(src, workspace=workspace), workspace


def test_shell_manifest_reports_quality_for_reviewed_geometry(tmp_path) -> None:
    asset, workspace = _registered_asset(tmp_path)
    plan = _plan_with_fragment(asset, reviewed=True, settings=_settings(sheet_thickness_mm=0.7))

    result = export_print_package(plan, tmp_path / "out", workspace=workspace, make_zip=True)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    shell = manifest["aligner_shells"]["artifacts"][0]

    assert result.aligner_shell_paths
    assert manifest["aligner_shells"]["manufacturing_readiness"]["verdict"] == "CONSISTENT"
    assert shell["quality"]["verdict"] == "CONSISTENT"
    assert shell["quality"]["connected_components"] == 1
    assert shell["quality"]["thickness_mm"]["p50"] == pytest.approx(0.7, abs=1e-3)
    assert manifest["hashes"]["aligner_shell_sha256"][shell["filename"]] == \
        result.artifact_sha256[shell["filename"]]


def test_shell_export_fails_closed_without_real_geometry(tmp_path) -> None:
    asset = MeshAsset(
        id="seg-x", format="stl-ascii", units=MeshUnits.MM, vertex_count=6,
        face_count=2, bounds=BoundingBox(min_xyz=(0, 0, 0), max_xyz=(2, 3, 1)),
    )
    plan = _plan_with_fragment(asset, reviewed=False, settings=_settings())

    result = export_print_package(plan, tmp_path / "out")
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.aligner_shell_paths == []
    assert result.aligner_shell_reports[0]["verdict"] == "NOT_APPLICABLE"
    assert "model-only" in result.aligner_shell_reports[0]["reason"]
    assert manifest["aligner_shells"]["manufacturing_readiness"]["verdict"] == "NOT_APPLICABLE"


def test_shell_export_reports_bad_geometry_as_issue(tmp_path) -> None:
    bad = """solid bad
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 0 0 0
      vertex 1 0 0
    endloop
  endfacet
endsolid bad
"""
    asset, workspace = _registered_asset(tmp_path, bad)
    plan = _plan_with_fragment(asset, reviewed=True, settings=_settings())

    result = export_print_package(plan, tmp_path / "out", workspace=workspace)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.aligner_shell_paths == []
    assert result.aligner_shell_reports[0]["verdict"] == "ISSUES"
    assert manifest["aligner_shells"]["manufacturing_readiness"]["verdict"] == "ISSUES"
