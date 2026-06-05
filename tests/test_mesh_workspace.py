from __future__ import annotations

from pathlib import Path

from orthoplan.mesh_workspace import read_registry, register_stl_mesh, resolve_mesh_path


ASCII_STL = """solid tooth
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid tooth
"""


def test_register_stl_mesh_copies_into_workspace(tmp_path: Path) -> None:
    source = tmp_path / "tooth_11.stl"
    source.write_text(ASCII_STL, encoding="utf-8")
    workspace = tmp_path / "workspace"

    asset = register_stl_mesh(source, workspace=workspace)

    registry = read_registry(workspace)
    assert asset.id in registry.entries
    resolved = resolve_mesh_path(asset.id, workspace=workspace)
    assert resolved is not None
    assert resolved.read_text(encoding="utf-8") == ASCII_STL


def test_resolve_mesh_path_rejects_unknown_or_unsafe_id(tmp_path: Path) -> None:
    assert resolve_mesh_path("../x", workspace=tmp_path) is None
    assert resolve_mesh_path("missing", workspace=tmp_path) is None
