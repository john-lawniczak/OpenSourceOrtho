"""Resolve published dataset scans and local mesh references with containment checks."""

from pathlib import Path

from orthoplan.datasets import resolve_published_asset
from orthoplan.io.mesh_import import is_supported_scan
from orthoplan.mesh_workspace import resolve_mesh_path


def resolve_scan_path(
    reference: object, *, ui_dir: Path, workspace: Path | None
) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        return None
    normalized = reference.strip()
    published = resolve_published_asset(normalized)
    if published is not None and is_supported_scan(published):
        return published
    if normalized.removeprefix("./").removeprefix("/").startswith("datasets/"):
        return None
    asset_id = normalized.removeprefix("/api/mesh/")
    asset_path = resolve_mesh_path(asset_id, workspace=workspace)
    if asset_path is not None:
        return asset_path
    relative = normalized.lstrip("./").lstrip("/")
    candidate = (ui_dir / relative).resolve()
    if (
        candidate.is_relative_to(ui_dir)
        and candidate.is_file()
        and is_supported_scan(candidate)
    ):
        return candidate
    return None
