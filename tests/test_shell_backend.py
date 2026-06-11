"""Robust shell backend selection and fail-closed fallback.

Open3D (the optional ``mesh-processing`` extra) is not installed in CI, so these
tests focus on the safety-critical path: when the robust backend is requested but
unavailable, the export must fall back to pure-Python AND record the downgrade -
never silently change geometry or crash.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orthoplan.aligner_shell_robust import RobustShellUnavailable, robust_shell_available
from orthoplan.mesh_workspace import register_stl_mesh
from orthoplan.model import (
    PrintExportSettings,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
)
from orthoplan.print_aligner import resolve_shell_backend
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


def _plan(asset, settings: TreatmentSettings) -> TreatmentPlan:
    return TreatmentPlan(
        id="backend-print",
        data={"segmented_teeth": True},
        settings=settings,
        mesh_assets=[asset],
        tooth_meshes=[
            SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id=asset.id, reviewed=True)
        ],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.1)])],
    )


def _registered_asset(tmp_path: Path):
    src = tmp_path / "frag.stl"
    src.write_text(_ASCII_STL, encoding="utf-8")
    return register_stl_mesh(src, workspace=tmp_path / "ws"), tmp_path / "ws"


def test_default_backend_is_pure_python() -> None:
    assert PrintExportSettings().shell_backend == "pure-python"


def test_resolve_backend_pure_python_has_no_fallback() -> None:
    resolved = resolve_shell_backend(PrintExportSettings(shell_backend="pure-python"))
    assert resolved["requested"] == "pure-python"
    assert resolved["used"] == "pure-python"
    assert resolved["fallback_reason"] is None


@pytest.mark.skipif(robust_shell_available(), reason="Open3D installed; tests the fail-closed path")
def test_resolve_backend_falls_back_when_open3d_missing() -> None:
    resolved = resolve_shell_backend(PrintExportSettings(shell_backend="robust"))
    assert resolved["requested"] == "robust"
    assert resolved["used"] == "pure-python"
    assert resolved["available"] is False
    assert "Open3D" in resolved["fallback_reason"]


@pytest.mark.skipif(robust_shell_available(), reason="Open3D installed; tests the fail-closed path")
def test_robust_build_raises_without_open3d() -> None:
    from orthoplan.aligner_shell_robust import build_robust_shell

    with pytest.raises(RobustShellUnavailable):
        build_robust_shell([], thickness_mm=0.6)


@pytest.mark.skipif(robust_shell_available(), reason="Open3D installed; tests the fail-closed path")
def test_export_records_backend_downgrade_in_manifest(tmp_path) -> None:
    asset, workspace = _registered_asset(tmp_path)
    plan = _plan(asset, _settings(shell_backend="robust"))

    result = export_print_package(plan, tmp_path / "out", workspace=workspace)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    backend = manifest["aligner_shells"]["backend"]

    # The shell was still produced (pure-Python), but the manifest is explicit
    # that the requested robust backend was unavailable - no silent substitution.
    assert result.aligner_shell_paths
    assert backend["requested"] == "robust"
    assert backend["used"] == "pure-python"
    assert backend["fallback_reason"]
    assert manifest["aligner_shells"]["artifacts"][0]["backend"] == "pure-python"
    assert result.aligner_shell_backend["used"] == "pure-python"
