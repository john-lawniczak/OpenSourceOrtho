"""Pure payload API for the occlusal proximity overlay (``POST /api/occlusion``).

Resolves a server-local upper AND lower whole-arch scan (the same references the
segmentation API accepts - never uploaded browser bytes), registers them into one
occlusal frame, builds the occlusal grid, and returns a classified proximity map
the 3D viewer paints red/amber/green. Like the other ``*_payload`` helpers it never
raises: errors come back as data.

On-device only (scans are PHI). Advisory geometry for review: never a measured
bite, contact force, occlusal analysis, or diagnosis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.occlusion.grid import build_occlusal_grid
from orthoplan.occlusion.proximity import (
    PROXIMITY_CAVEAT,
    classify_proximity,
    proximity_map_to_dict,
)
from orthoplan.occlusion.registration import register_bite, registration_to_dict
from orthoplan.segmentation_api import _resolve_scan_path, _scan_arch, _scan_list


def _resolve_arches(
    payload: dict[str, Any], *, ui_root: Path, workspace: str | Path | None
) -> tuple[list, list, list[str]]:
    """Resolve the payload's scans into (upper_vertices, lower_vertices, errors)."""

    upper: list = []
    lower: list = []
    errors: list[str] = []
    for scan in _scan_list(payload):
        reference = scan.get("reference") or scan.get("url")
        path = _resolve_scan_path(reference, ui_dir=ui_root, workspace=workspace)
        if path is None:
            errors.append(f"could not resolve scan: {reference!r}")
            continue
        arch = _scan_arch(scan, path)
        if arch is None:
            errors.append(f"could not determine arch for scan: {reference!r}")
            continue
        _asset, vertices = read_stl_geometry(path)
        if arch == "maxillary":
            upper = vertices
        else:
            lower = vertices
    return upper, lower, errors


def proximity_payload(
    payload: dict[str, Any], *, ui_dir: str | Path, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Register an upper/lower scan pair and return a classified occlusal proximity map."""

    try:
        ui_root = Path(ui_dir).resolve()
        upper, lower, errors = _resolve_arches(payload, ui_root=ui_root, workspace=workspace)
        if not upper or not lower:
            return {
                "ok": False,
                "errors": errors or ["need both an upper and a lower scan for occlusion"],
            }

        units_confirmed = bool(payload.get("units_confirmed", False))
        registration = register_bite(upper, lower, units_confirmed=units_confirmed)
        if registration.mode == "unavailable":
            return {"ok": False, "errors": [registration.notes]}

        grid = build_occlusal_grid(upper, lower, lower_offset=registration.lower_offset)
        pmap = classify_proximity(grid, registration, units_confirmed=units_confirmed)
        return {
            "ok": True,
            "requires_review": True,
            "caveat": PROXIMITY_CAVEAT,
            "registration": registration_to_dict(registration),
            "proximity": proximity_map_to_dict(pmap),
            "warnings": errors,
        }
    except Exception as exc:  # noqa: BLE001 - payload API must never raise
        return {"ok": False, "errors": [f"occlusion proximity failed: {exc}"]}
