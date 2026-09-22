"""Every supported scan format reduces to the same geometry."""

from __future__ import annotations

from pathlib import Path

import pytest

from orthoplan.io.mesh_formats import MeshParseError, parse_bytes, parse_file, sniff_family
from tests import scan_fixtures as fixtures

SPAN = 10.0


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("name", "data", "expected_format"),
    [
        ("t.stl", fixtures.stl_ascii(), "stl-ascii"),
        ("t.ply", fixtures.ply_ascii(), "ply-ascii"),
        ("le.ply", fixtures.ply_binary(), "ply-le"),
        ("be.ply", fixtures.ply_binary(big_endian=True), "ply-be"),
        ("t.obj", fixtures.obj(), "obj"),
        ("t.3mf", fixtures.three_mf(), "3mf"),
        ("t.gltf", fixtures.gltf(), "gltf"),
        ("t.glb", fixtures.glb(), "glb"),
        ("t.fbx", fixtures.fbx_ascii(), "fbx-ascii"),
        ("b.fbx", fixtures.fbx_binary(), "fbx-binary"),
        ("z.fbx", fixtures.fbx_binary(compressed=True), "fbx-binary"),
    ],
)
def test_every_mesh_format_yields_the_same_four_triangles(
    tmp_path: Path, name: str, data: bytes, expected_format: str
) -> None:
    payload = parse_file(_write(tmp_path, name, data))

    assert payload.source_format == expected_format
    assert payload.kind == "mesh"
    assert payload.face_count == len(fixtures.FACES)
    assert sorted(payload.triangles()) == sorted(fixtures.triangles())


@pytest.mark.parametrize(
    ("name", "data", "expected_format"),
    [
        ("cloud.ply", fixtures.ply_ascii(with_faces=False), "ply-ascii-points"),
        ("cloud.obj", fixtures.obj(with_faces=False), "obj-points"),
        ("cloud.asc", fixtures.asc_points(), "asc-points"),
    ],
)
def test_faceless_exports_are_read_as_point_clouds(
    tmp_path: Path, name: str, data: bytes, expected_format: str
) -> None:
    payload = parse_file(_write(tmp_path, name, data))

    assert payload.kind == "points"
    assert payload.source_format == expected_format
    assert payload.faces == []
    # Points are returned as points, never regrouped into invented triangles.
    assert payload.triangle_soup() == payload.points
    assert set(fixtures.POINTS).issubset(set(payload.points))


def test_only_3mf_gltf_and_fbx_declare_a_unit(tmp_path: Path) -> None:
    assert parse_bytes(fixtures.three_mf(), suffix=".3mf").declared_units == "millimeter"
    assert parse_bytes(fixtures.gltf(), suffix=".gltf").declared_units == "meter"
    assert parse_bytes(fixtures.fbx_ascii(), suffix=".fbx").declared_units == "millimeter"
    assert parse_bytes(fixtures.stl_ascii(), suffix=".stl").declared_units is None
    assert parse_bytes(fixtures.ply_ascii(), suffix=".ply").declared_units is None


def test_unrecognised_fbx_unit_scale_is_reported_not_guessed() -> None:
    payload = parse_bytes(fixtures.fbx_ascii(unit_scale=7.3), suffix=".fbx")

    assert payload.declared_units is None
    assert any("7.3" in note for note in payload.notes)


def test_gltf_node_transforms_are_applied(tmp_path: Path) -> None:
    payload = parse_bytes(fixtures.gltf(scale=2.0), suffix=".gltf")

    assert max(value for point in payload.points for value in point) == pytest.approx(2 * SPAN)


def test_gltf_reads_an_external_buffer_beside_the_document(tmp_path: Path) -> None:
    (tmp_path / "side.bin").write_bytes(fixtures.gltf_sidecar_buffer())
    path = _write(tmp_path, "side.gltf", fixtures.gltf(uri="side.bin"))

    assert parse_file(path).face_count == len(fixtures.FACES)


def test_gltf_refuses_to_fetch_a_remote_buffer(tmp_path: Path) -> None:
    path = _write(tmp_path, "remote.gltf", fixtures.gltf(uri="https://example.invalid/x.bin"))

    with pytest.raises(MeshParseError, match="remote URI"):
        parse_file(path)


def test_gltf_refuses_a_buffer_outside_its_own_directory(tmp_path: Path) -> None:
    (tmp_path / "secret.bin").write_bytes(b"x")
    nested = tmp_path / "scan"
    nested.mkdir()
    path = _write(nested, "escape.gltf", fixtures.gltf(uri="../secret.bin"))

    with pytest.raises(MeshParseError, match="missing next to"):
        parse_file(path)


def test_obj_resolves_negative_and_relative_face_indices(tmp_path: Path) -> None:
    source = b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n"

    payload = parse_bytes(source, suffix=".obj")

    assert payload.faces == [(0, 1, 2)]


def test_obj_rejects_a_face_index_past_the_vertices_declared_before_it() -> None:
    with pytest.raises(MeshParseError, match="outside the vertices"):
        parse_bytes(b"v 0 0 0\nf 1 2 3\n", suffix=".obj")


def test_polygons_larger_than_a_triangle_are_fan_triangulated() -> None:
    quad = b"v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n"

    assert parse_bytes(quad, suffix=".obj").faces == [(0, 1, 2), (0, 2, 3)]


def test_a_mislabelled_export_is_read_by_content_not_extension(tmp_path: Path) -> None:
    # A PLY the user renamed to .obj (or that a scanner mislabelled) still imports.
    path = _write(tmp_path, "upper.obj", fixtures.ply_ascii())

    assert parse_file(path).source_format == "ply-ascii"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (fixtures.glb(), "gltf"),
        (fixtures.fbx_binary(), "fbx"),
        (fixtures.three_mf(), "3mf"),
        (fixtures.ply_ascii(), "ply"),
        (fixtures.stl_ascii(), "stl"),
        (fixtures.obj(), "obj"),
        (b"0 0 0\n1 1 1\n2 2 2\n", "points"),
        (b"\x00\x01\x02 not a scan", None),
    ],
)
def test_content_sniffing_identifies_each_family(data: bytes, expected: str | None) -> None:
    assert sniff_family(data) == expected


def test_an_unsupported_extension_names_what_is_supported() -> None:
    with pytest.raises(MeshParseError, match="supported formats"):
        parse_bytes(b"\x00\x01\x02 not a scan", suffix=".txt")


def test_an_empty_file_is_rejected() -> None:
    with pytest.raises(MeshParseError, match="empty"):
        parse_bytes(b"", suffix=".stl")


def test_a_face_referencing_a_missing_vertex_is_rejected() -> None:
    broken = fixtures.ply_ascii().replace(b"3 1 2 3", b"3 1 2 99")

    with pytest.raises(MeshParseError, match="outside the vertex list"):
        parse_bytes(broken, suffix=".ply")


def test_non_finite_coordinates_are_rejected() -> None:
    with pytest.raises(MeshParseError, match="finite"):
        parse_bytes(b"v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", suffix=".obj")


def test_a_text_file_of_prose_is_not_mistaken_for_a_point_cloud() -> None:
    with pytest.raises(MeshParseError):
        parse_bytes(b"these are notes\nabout the scan\nnot coordinates\n", suffix=".asc")


def test_3mf_without_a_model_part_is_rejected() -> None:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "no model here")

    with pytest.raises(MeshParseError, match="no 3D model part"):
        parse_bytes(buffer.getvalue(), suffix=".3mf")
