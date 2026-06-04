from __future__ import annotations

import struct
from pathlib import Path

import pytest

from orthoplan.io.stl_import import inspect_stl
from orthoplan.model import MeshAsset, MeshUnits, bounding_box_sanity


def _write_binary_stl(path: Path, triangles: list[tuple[float, ...]]) -> None:
    payload = b"\x00" * 80 + struct.pack("<I", len(triangles))
    for tri in triangles:
        payload += struct.pack("<12f", *tri) + b"\x00\x00"
    path.write_bytes(payload)


def test_inspect_stl_reports_unverified_units_and_counts(tmp_path: Path) -> None:
    stl = tmp_path / "patient_jane" / "scan.stl"
    stl.parent.mkdir()
    # one triangle: normal + 3 vertices spanning ~10x12 mm
    _write_binary_stl(stl, [(0, 0, 1, 0, 0, 0, 10, 0, 0, 0, 12, 0)])

    asset = inspect_stl(stl)

    assert asset.format == "stl-binary"
    assert asset.face_count == 1
    assert asset.vertex_count == 3
    assert asset.quality is not None
    assert asset.quality.degenerate_faces == 0
    assert asset.units is MeshUnits.UNVERIFIED
    # reference is redacted to a basename: no directory (patient name) survives.
    assert asset.reference == "scan.stl"
    assert asset.sha256 is not None


def test_absolute_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="relative"):
        MeshAsset(
            id="x",
            format="stl-binary",
            vertex_count=0,
            face_count=0,
            reference="/Users/patient_doe/scan.stl",
        )


def test_bounding_box_sanity_flags_unverified_units(tmp_path: Path) -> None:
    stl = tmp_path / "scan.stl"
    _write_binary_stl(stl, [(0, 0, 1, 0, 0, 0, 10, 0, 0, 0, 12, 0)])
    asset = inspect_stl(stl)
    assert "unverified" in (bounding_box_sanity(asset) or "")


def test_inspect_stl_rejects_non_stl_text(tmp_path: Path) -> None:
    path = tmp_path / "not_a_scan.stl"
    path.write_text("hello, not actually a mesh", encoding="utf-8")

    with pytest.raises(ValueError, match="no readable facets"):
        inspect_stl(path)


def test_inspect_stl_rejects_bad_ascii_vertex(tmp_path: Path) -> None:
    path = tmp_path / "bad_ascii.stl"
    path.write_text(
        "\n".join(
            [
                "solid bad",
                "facet normal 0 0 1",
                "outer loop",
                "vertex 0 nope 0",
                "endloop",
                "endfacet",
                "endsolid bad",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid STL vertex"):
        inspect_stl(path)


def test_inspect_stl_rejects_ascii_facet_vertex_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "mismatch.stl"
    path.write_text(
        "\n".join(
            [
                "solid mismatch",
                "facet normal 0 0 1",
                "outer loop",
                "vertex 0 0 0",
                "endloop",
                "endfacet",
                "endsolid mismatch",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="inconsistent"):
        inspect_stl(path)


def test_inspect_stl_rejects_oversized_file_before_reading(tmp_path: Path) -> None:
    path = tmp_path / "large.stl"
    path.write_bytes(b"x" * 8)

    with pytest.raises(ValueError, match="too large"):
        inspect_stl(path, max_bytes=4)


def test_inspect_stl_reports_degenerate_faces(tmp_path: Path) -> None:
    stl = tmp_path / "degenerate.stl"
    _write_binary_stl(stl, [(0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)])

    asset = inspect_stl(stl)

    assert asset.quality is not None
    assert asset.quality.degenerate_faces == 1
    assert asset.quality.notes
