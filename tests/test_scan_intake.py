"""Multi-format intake: asset metadata, canonical storage, and fail-closed points."""

from __future__ import annotations

from pathlib import Path

import pytest

from orthoplan.io.mesh_import import MAX_SCAN_BYTES, inspect_mesh, is_supported_scan, read_scan
from orthoplan.io.stl_export import CANONICAL_STL_HEADER, binary_stl_bytes
from orthoplan.mesh_geometry import reviewed_fragment_triangles
from orthoplan.mesh_workspace import read_registry, register_scan_mesh, resolve_mesh_path
from orthoplan.model.assets import MeshProvenance, MeshUnits
from orthoplan.model.plan import SegmentedToothMesh, ToothId
from tests import scan_fixtures as fixtures


def _scan(tmp_path: Path, name: str, data: bytes) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("upper.ply", fixtures.ply_ascii()),
        ("upper.obj", fixtures.obj()),
        ("upper.3mf", fixtures.three_mf()),
        ("upper.glb", fixtures.glb()),
        ("upper.fbx", fixtures.fbx_binary()),
    ],
)
def test_any_mesh_format_produces_a_redacted_units_unverified_asset(
    tmp_path: Path, name: str, data: bytes
) -> None:
    asset = inspect_mesh(_scan(tmp_path, name, data))

    assert asset.units is MeshUnits.UNVERIFIED, "a file's own claim never confirms units"
    assert asset.geometry_kind == "mesh"
    assert asset.face_count == len(fixtures.FACES)
    assert asset.bounds is not None and asset.bounds.max_span == pytest.approx(10.0)
    assert asset.reference == name, "only the basename survives; directories can carry PHI"


def test_a_declared_unit_is_reported_but_never_applied(tmp_path: Path) -> None:
    asset = inspect_mesh(_scan(tmp_path, "upper.3mf", fixtures.three_mf()))

    assert asset.declared_units is MeshUnits.MM
    assert asset.units is MeshUnits.UNVERIFIED
    assert asset.units_confirmed is False


def test_a_point_cloud_is_accepted_and_marked_as_having_no_surface(tmp_path: Path) -> None:
    scan = read_scan(_scan(tmp_path, "cloud.asc", fixtures.asc_points()))

    assert scan.asset.geometry_kind == "points"
    assert scan.asset.face_count == 0
    assert scan.asset.has_surface is False
    assert scan.vertices == scan.payload.points
    assert scan.asset.quality is not None
    assert any("point cloud" in note for note in scan.asset.quality.notes)


def test_a_mesh_asset_reports_a_surface(tmp_path: Path) -> None:
    assert inspect_mesh(_scan(tmp_path, "upper.ply", fixtures.ply_ascii())).has_surface is True


def test_the_same_export_always_resolves_to_the_same_asset_id(tmp_path: Path) -> None:
    first = inspect_mesh(_scan(tmp_path / "a", "upper.glb", fixtures.glb()))
    second = inspect_mesh(_scan(tmp_path / "b", "renamed.glb", fixtures.glb()))

    assert first.id == second.id, "the id hashes the uploaded bytes, not the path"


def test_an_oversized_file_is_refused_before_it_is_read(tmp_path: Path) -> None:
    path = _scan(tmp_path, "upper.ply", fixtures.ply_ascii())

    with pytest.raises(ValueError, match="too large"):
        inspect_mesh(path, max_bytes=4)


def test_supported_suffix_check_covers_every_reader() -> None:
    for name in ("a.stl", "a.ply", "a.obj", "a.asc", "a.xyz", "a.pts", "a.3mf", "a.gltf", "a.glb", "a.fbx"):
        assert is_supported_scan(name), name
    assert not is_supported_scan("notes.txt")


def test_max_scan_bytes_is_a_real_bound() -> None:
    assert MAX_SCAN_BYTES == 100 * 1024 * 1024


def test_registration_canonicalizes_a_mesh_to_binary_stl(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    asset = register_scan_mesh(_scan(tmp_path, "upper.ply", fixtures.ply_ascii()), workspace=workspace)

    stored = resolve_mesh_path(asset.id, workspace=workspace)
    assert stored is not None and stored.suffix == ".stl"
    assert stored.read_bytes() == binary_stl_bytes(fixtures.triangles(), header=CANONICAL_STL_HEADER)
    entry = read_registry(workspace).entries[asset.id]
    assert entry.source_format == "ply-ascii", "the original format stays on the record"
    assert entry.geometry_kind == "mesh"


def test_registration_canonicalizes_a_point_cloud_to_xyz(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    asset = register_scan_mesh(_scan(tmp_path, "cloud.asc", fixtures.asc_points()), workspace=workspace)

    stored = resolve_mesh_path(asset.id, workspace=workspace)
    assert stored is not None and stored.suffix == ".xyz"
    assert stored.read_text().splitlines()[0] == "10.000000 0.000000 0.000000"
    assert read_registry(workspace).entries[asset.id].geometry_kind == "points"


def test_an_uploaded_stl_is_stored_byte_for_byte(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = _scan(tmp_path, "upper.stl", fixtures.stl_ascii())

    asset = register_scan_mesh(source, workspace=workspace)

    stored = resolve_mesh_path(asset.id, workspace=workspace)
    assert stored is not None and stored.read_bytes() == source.read_bytes()


def test_a_canonical_scan_reimports_to_the_same_geometry(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    asset = register_scan_mesh(_scan(tmp_path, "upper.fbx", fixtures.fbx_binary()), workspace=workspace)

    reread = read_scan(resolve_mesh_path(asset.id, workspace=workspace))

    assert sorted(reread.payload.triangles()) == sorted(fixtures.triangles())


def test_a_point_cloud_fragment_yields_no_triangles(tmp_path: Path) -> None:
    """A cloud must never be regrouped three-points-at-a-time into fake faces."""

    workspace = tmp_path / "workspace"
    asset = register_scan_mesh(
        _scan(tmp_path, "cloud.ply", fixtures.ply_ascii(with_faces=False)),
        workspace=workspace,
        provenance=MeshProvenance.MODEL_GENERATED,
    )
    link = SegmentedToothMesh(
        tooth=ToothId(value="11"),
        mesh_asset_id=asset.id,
        source=MeshProvenance.MODEL_GENERATED,
        reviewed=True,
    )

    assert reviewed_fragment_triangles(link, workspace=workspace) is None


def test_a_reviewed_mesh_fragment_still_yields_its_triangles(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    asset = register_scan_mesh(
        _scan(tmp_path, "tooth.ply", fixtures.ply_ascii()),
        workspace=workspace,
        provenance=MeshProvenance.MODEL_GENERATED,
    )
    link = SegmentedToothMesh(
        tooth=ToothId(value="11"),
        mesh_asset_id=asset.id,
        source=MeshProvenance.MODEL_GENERATED,
        reviewed=True,
    )

    triangles = reviewed_fragment_triangles(link, workspace=workspace)

    assert triangles is not None and len(triangles) == len(fixtures.FACES)
