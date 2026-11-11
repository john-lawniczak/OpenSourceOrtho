from concurrent.futures import ThreadPoolExecutor
from orthoplan.io.stl_export import binary_stl_bytes
from orthoplan.mesh_workspace import register_scan_mesh, read_registry, resolve_mesh_path


def test_parallel_uploads_preserve_every_registry_entry(tmp_path):
    paths = []
    for i in range(12):
        path = tmp_path / f"{i}.stl"
        path.write_bytes(binary_stl_bytes([((i, 0, 0), (i + 1, 0, 0), (i, 1, 0))]))
        paths.append(path)
    workspace = tmp_path / "workspace"
    with ThreadPoolExecutor(max_workers=6) as pool:
        assets = list(pool.map(lambda p: register_scan_mesh(p, workspace=workspace), paths))
    assert len(read_registry(workspace).entries) == 12
    assert all(resolve_mesh_path(a.id, workspace=workspace) for a in assets)
