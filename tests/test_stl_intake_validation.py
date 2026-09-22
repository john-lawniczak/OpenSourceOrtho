"""Malformed scan coordinates must fail before geometry processing."""
import struct

import pytest

from orthoplan.io.stl_import import read_stl_geometry


@pytest.mark.parametrize("coordinate", ["nan", "inf", "-inf"])
@pytest.mark.parametrize("binary", [False, True])
def test_nonfinite_coordinates_rejected(tmp_path, coordinate, binary):
    path = tmp_path / "scan.stl"
    if binary:
        values = (0, 0, 1, 0, 0, 0, 1, 0, 0, float(coordinate), 1, 0)
        path.write_bytes(b"\0" * 80 + struct.pack("<I12fH", 1, *values, 0))
    else:
        path.write_text(
            f"solid scan\nfacet normal 0 0 1\nouter loop\n"
            f"vertex 0 0 0\nvertex 1 0 0\nvertex {coordinate} 1 0\n"
            "endloop\nendfacet\nendsolid scan\n"
        )
    with pytest.raises(ValueError, match="must be finite"):
        read_stl_geometry(path)


@pytest.mark.parametrize("extra", ["vertex 2 2 2", "vertex 2 2", "vertex 2 2 2 2"])
def test_extra_or_malformed_vertices_rejected(tmp_path, extra):
    path = tmp_path / "scan.stl"
    path.write_text(
        "solid scan\nfacet normal 0 0 1\nouter loop\n"
        f"vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n{extra}\n"
        "endloop\nendfacet\nendsolid scan\n"
    )
    with pytest.raises(ValueError, match="inconsistent|invalid STL vertex"):
        read_stl_geometry(path)
