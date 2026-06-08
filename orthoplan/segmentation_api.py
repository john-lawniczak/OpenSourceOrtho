"""Pure payload API for on-device tooth segmentation (``POST /api/segment``).

Resolves a server-local whole-arch scan (a UI example scan or a registered mesh
asset - never uploaded bytes, which never leave the browser), runs the local
segmenter, writes per-tooth meshes into the mesh workspace, and returns a
REVIEWABLE proposal: per-tooth confidence plus a ready-to-merge plan fragment
(``mesh_assets`` + ``tooth_meshes``). It never auto-applies anything and, like the
other ``*_payload`` helpers, never raises - errors come back as data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orthoplan.io.stl_import import read_stl_geometry
from orthoplan.mesh_workspace import resolve_mesh_path
from orthoplan.model.assets import ArchName, MeshAsset, MeshProvenance
from orthoplan.model.plan import SegmentedToothMesh, ToothId
from orthoplan.planning.mesh_frame import compute_local_frame
from orthoplan.segmentation.auto import (
    SEGMENTATION_CAVEAT,
    ProposedTooth,
    build_advisory_findings,
    build_count_advisories,
    load_local_segmenter,
    tooth_values_for_arch,
)
from orthoplan.segmentation.mesh_export import write_segment_meshes


def _resolve_scan_path(
    reference: object, *, ui_dir: Path, workspace: Path | None
) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        return None
    asset_path = resolve_mesh_path(reference.strip(), workspace=workspace)
    if asset_path is not None:
        return asset_path
    relative = reference.strip().lstrip("./").lstrip("/")
    candidate = (ui_dir / relative).resolve()
    if (
        candidate.is_relative_to(ui_dir)
        and candidate.is_file()
        and candidate.suffix.lower() == ".stl"
    ):
        return candidate
    return None


def _scan_arch(scan: dict[str, Any], path: Path) -> ArchName | None:
    arch = scan.get("arch")
    if arch in ("maxillary", "mandibular"):
        return arch  # type: ignore[return-value]
    name = path.name.lower()
    if any(token in name for token in ("upper", "maxill", "-u.", "_u.")):
        return "maxillary"
    if any(token in name for token in ("lower", "mandib", "-l.", "_l.")):
        return "mandibular"
    return None


def _scan_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("scans"), list):
        return [scan for scan in payload["scans"] if isinstance(scan, dict)]
    if payload.get("reference"):
        return [payload]
    return []


def _missing_teeth(payload: dict[str, Any]) -> list[str]:
    """FDI numbers the user marked as absent, used to anchor segmentation labels."""

    raw = payload.get("missing_teeth")
    if not isinstance(raw, list):
        return []
    return [str(tooth).strip() for tooth in raw if str(tooth).strip()]


def _segment_one_scan(
    scan: dict[str, Any],
    segmenter,
    *,
    ui_root: Path,
    workspace: str | Path | None,
    missing_teeth: list[str] | None = None,
) -> tuple[list[ProposedTooth], list[MeshAsset], list[SegmentedToothMesh], str | None]:
    """Segment a single scan dict. Returns (proposed, assets, links, error)."""

    reference = scan.get("reference") or scan.get("url")
    path = _resolve_scan_path(reference, ui_dir=ui_root, workspace=workspace)
    if path is None:
        return [], [], [], f"could not resolve scan: {reference!r}"
    arch = _scan_arch(scan, path)
    if arch is None:
        return [], [], [], f"could not determine arch for scan: {reference!r}"

    _asset, vertices = read_stl_geometry(path)
    # User-marked gaps anchor the FDI labels for this arch; None lets the segmenter
    # detect the tooth count itself.
    tooth_values = tooth_values_for_arch(arch, missing_teeth)
    segments = segmenter.segment(vertices, arch=arch, tooth_values=tooth_values)
    proposed: list[ProposedTooth] = []
    assets: list[MeshAsset] = []
    links: list[SegmentedToothMesh] = []
    for segment, mesh_asset in write_segment_meshes(segments, workspace=workspace):
        assets.append(mesh_asset)
        flat = [v for tri in segment.triangles for v in tri]
        links.append(
            SegmentedToothMesh(
                tooth=ToothId(value=segment.tooth_value),
                mesh_asset_id=mesh_asset.id,
                source=MeshProvenance.MODEL_GENERATED,
                local_frame=compute_local_frame(flat),
                notes=f"auto-segment draft (confidence {segment.confidence:.2f})",
            )
        )
        proposed.append(
            ProposedTooth(
                arch=arch,
                tooth=segment.tooth_value,
                confidence=segment.confidence,
                mesh_asset_id=mesh_asset.id,
                url=f"/api/mesh/{mesh_asset.id}",
                centroid=segment.centroid,
                vertex_count=segment.vertex_count,
            )
        )
    return proposed, assets, links, None


def segment_payload(
    payload: dict[str, Any], *, ui_dir: str | Path, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Segment one or more server-local scans into a reviewable proposal."""

    try:
        ui_root = Path(ui_dir).resolve()
        scans = _scan_list(payload)
        if not scans:
            return {"ok": False, "errors": ["no scan reference provided"]}

        segmenter = load_local_segmenter()
        missing_teeth = _missing_teeth(payload)
        proposed: list[ProposedTooth] = []
        assets_by_id: dict[str, MeshAsset] = {}
        links: list[SegmentedToothMesh] = []
        errors: list[str] = []
        resolved_any = False
        for scan in scans:
            rows, assets, scan_links, error = _segment_one_scan(
                scan, segmenter, ui_root=ui_root, workspace=workspace, missing_teeth=missing_teeth
            )
            if error:
                errors.append(error)
                continue
            resolved_any = True
            proposed.extend(rows)
            links.extend(scan_links)
            for asset in assets:
                assets_by_id[asset.id] = asset

        if not resolved_any:
            return {"ok": False, "errors": errors or ["no scan could be segmented"]}

        overall = (
            round(sum(p.confidence for p in proposed) / len(proposed), 3) if proposed else 0.0
        )
        count_by_arch: dict[ArchName, int] = {}
        for tooth in proposed:
            count_by_arch[tooth.arch] = count_by_arch.get(tooth.arch, 0) + 1
        advisory_findings = build_advisory_findings(overall) + build_count_advisories(count_by_arch)
        return {
            "ok": True,
            "model": _segmenter_metadata(segmenter),
            "method": _SEGMENTATION_METHOD,
            "requires_review": True,
            "caveat": SEGMENTATION_CAVEAT,
            "advisory_findings": [
                finding.model_dump(mode="json") for finding in advisory_findings
            ],
            "teeth": [tooth.model_dump(mode="json") for tooth in proposed],
            "overall_confidence": overall,
            "warnings": errors,
            "plan_fragment": {
                "mesh_assets": [asset.model_dump(mode="json") for asset in assets_by_id.values()],
                "tooth_meshes": [link.model_dump(mode="json") for link in links],
            },
        }
    except Exception as exc:  # noqa: BLE001 - payload API must never raise
        return {"ok": False, "errors": [f"segmentation failed: {exc}"]}


_SEGMENTATION_METHOD = (
    "Hybrid geometry proposal: arch-position graph cuts scored by "
    "height valleys, curvature, and face-normal changes."
)


def _segmenter_metadata(segmenter) -> dict[str, str]:
    return {
        "name": segmenter.name,
        "version": segmenter.version,
        "backend": getattr(segmenter, "backend", "pure-python"),
    }
