from __future__ import annotations

import struct
from pathlib import Path

import pytest

from orthoplan.model import MeshProvenance, ToothId, TreatmentPlan
from orthoplan.segmentation import import_segmented_meshes


def _write_binary_stl(path: Path, triangles: list[tuple[float, ...]]) -> None:
    payload = b"\x00" * 80 + struct.pack("<I", len(triangles))
    for tri in triangles:
        payload += struct.pack("<12f", *tri) + b"\x00\x00"
    path.write_bytes(payload)


def test_import_segmented_meshes_links_each_tooth(tmp_path: Path) -> None:
    stl_11 = tmp_path / "t11.stl"
    stl_21 = tmp_path / "t21.stl"
    _write_binary_stl(stl_11, [(0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 6, 0)])
    _write_binary_stl(stl_21, [(0, 0, 1, 0, 0, 0, 7, 0, 0, 0, 8, 0)])

    assets, links = import_segmented_meshes(
        {ToothId(value="11"): stl_11, ToothId(value="21"): stl_21}
    )

    assert len(assets) == 2
    assert {link.tooth.value for link in links} == {"11", "21"}
    assert all(link.source is MeshProvenance.IMPORTED for link in links)

    # Results drop straight into a plan and validate.
    plan = TreatmentPlan(id="seg", mesh_assets=assets, tooth_meshes=links)
    assert plan.segmented_tooth_values == {"11", "21"}


def test_import_attaches_approximate_local_frame(tmp_path: Path) -> None:
    stl = tmp_path / "t11.stl"
    # Two triangles giving a non-degenerate, anisotropic point cloud.
    _write_binary_stl(
        stl,
        [
            (0, 0, 1, 0, 0, 0, 8, 0, 0, 0, 3, 0),
            (0, 0, 1, 8, 0, 0, 8, 3, 0, 0, 3, 0),
        ],
    )
    _, links = import_segmented_meshes({ToothId(value="11"): stl})
    frame = links[0].local_frame
    assert frame is not None
    assert frame.approximate is True
    assert frame.source == "pca-crown"
    assert "not anatomy" in frame.note.lower()


def test_identical_mesh_for_two_teeth_is_rejected(tmp_path: Path) -> None:
    stl = tmp_path / "shared.stl"
    _write_binary_stl(stl, [(0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 6, 0)])
    with pytest.raises(ValueError, match="identical mesh content"):
        import_segmented_meshes({ToothId(value="11"): stl, ToothId(value="21"): stl})
