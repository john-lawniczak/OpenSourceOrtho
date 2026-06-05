from __future__ import annotations

import json
import zipfile
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan import __version__
from orthoplan.hashing import canonical_json, sha256_bytes, sha256_text
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.assets import BoundingBox
from orthoplan.model.plan import TreatmentPlan
from orthoplan.printing import PRINT_EXPORT_CAVEAT, build_print_export_status
from orthoplan.viz.progress import build_stage_progress_frames


class PrintPackageResult(BaseModel):
    output_dir: str
    manifest_path: str
    artifact_paths: list[str] = Field(default_factory=list)
    artifact_sha256: dict[str, str] = Field(default_factory=dict)
    manifest_sha256: str
    zip_path: str | None = None
    zip_sha256: str | None = None
    email_draft_path: str | None = None
    caveat: str = PRINT_EXPORT_CAVEAT


def export_print_package(
    plan: TreatmentPlan,
    output_dir: str | Path,
    *,
    make_zip: bool = False,
    make_email_draft: bool = False,
) -> PrintPackageResult:
    """Generate stage proxy STL files, a manifest, and optional zip/email draft."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(plan.id)
    status = build_print_export_status(plan)
    frames = build_stage_progress_frames(plan)
    artifacts, records = _write_stage_artifacts(plan, output, frames, stem)
    manifest_path = _write_manifest(plan, output, status, records, frames, stem)
    zip_path = (
        _write_zip(stem, output, [manifest_path, *[Path(path) for path in artifacts]])
        if make_zip
        else None
    )
    email_path = (
        _write_email_draft(plan, output, zip_path or manifest_path, status.delivery_email, stem)
        if make_email_draft
        else None
    )
    return PrintPackageResult(
        output_dir=str(output),
        manifest_path=str(manifest_path),
        artifact_paths=artifacts,
        artifact_sha256={record["filename"]: record["sha256"] for record in records},
        manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
        zip_path=str(zip_path) if zip_path else None,
        zip_sha256=sha256_bytes(zip_path.read_bytes()) if zip_path else None,
        email_draft_path=str(email_path) if email_path else None,
    )


def _write_stage_artifacts(
    plan: TreatmentPlan,
    output: Path,
    frames: list,
    stem: str,
) -> tuple[list[str], list[dict]]:
    artifacts: list[str] = []
    records: list[dict] = []
    tooth_geometry = _tooth_geometry(plan)
    for frame in frames:
        path = output / f"{stem}-stage-{frame.stage_index:02d}-model.stl"
        stl, geometry_sources = _frame_to_stl(
            stem,
            frame.stage_index,
            frame.poses,
            tooth_geometry,
        )
        path.write_text(stl, encoding="utf-8")
        artifacts.append(str(path))
        records.append(_artifact_record(path, frame.stage_index, geometry_sources))
    return artifacts, records


def _artifact_record(path: Path, stage_index: int, geometry_sources: list[dict]) -> dict:
    return {
        "filename": path.name,
        "stage_index": stage_index,
        "format": "stl-ascii",
        "sha256": sha256_bytes(path.read_bytes()),
        "byte_size": path.stat().st_size,
        "geometry_sources": geometry_sources,
    }


def _write_manifest(
    plan: TreatmentPlan,
    output: Path,
    status,
    artifacts: list[dict],
    frames: list,
    stem: str,
) -> Path:
    plan_payload = json.loads(plan_to_json(plan, indent=None))
    manifest = {
        "schema": "orthoplan-print-package-v1",
        "engine": {"name": "orthoplan", "version": __version__},
        "plan_id": plan.id,
        "title": plan.title,
        "plan_sha256": sha256_text(canonical_json(plan_payload)),
        "stage_frames_sha256": sha256_text(canonical_json([f.model_dump() for f in frames])),
        "ready": status.ready,
        "blockers": status.blockers,
        "artifacts": artifacts,
        "delivery_email": status.delivery_email,
        "model_material": status.model_material,
        "thermoforming_material": status.thermoforming_material,
        "post_processing_notes": status.post_processing_notes,
        "caveat": status.caveat,
    }
    path = output / f"{stem}-print-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_zip(plan_id: str, output: Path, paths: list[Path]) -> Path:
    zip_path = output / f"{plan_id}-print-package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in paths:
            info = zipfile.ZipInfo(path.name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return zip_path


def _write_email_draft(
    plan: TreatmentPlan,
    output: Path,
    attachment: Path,
    delivery_email: str | None,
    stem: str,
) -> Path:
    message = EmailMessage()
    message["Subject"] = f"OpenSource Ortho print package: {plan.id}"
    message["To"] = delivery_email or ""
    message["From"] = ""
    message.set_content(
        "Attached is the generated OpenSource Ortho print package.\n\n"
        f"{PRINT_EXPORT_CAVEAT}\n"
    )
    message.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="octet-stream",
        filename=attachment.name,
    )
    path = output / f"{stem}-print-package.eml"
    path.write_bytes(message.as_bytes())
    return path


def _safe_stem(plan_id: str) -> str:
    """Filesystem-safe filename stem derived from an author-supplied plan id.

    Plan ids come from JSON that may be imported from an untrusted source and
    flow into output filenames. Restrict them to a conservative charset so an id
    containing path separators or traversal sequences (``..``, ``/``) cannot be
    used to write artifacts outside the chosen output directory.
    """

    cleaned = "".join(char if (char.isalnum() or char in {"-", "_"}) else "-" for char in plan_id)
    return cleaned.strip("-") or "plan"


def _tooth_geometry(plan: TreatmentPlan) -> dict[str, tuple[str, tuple[float, float, float]]]:
    assets = {asset.id: asset for asset in plan.mesh_assets}
    assets.update({scan.asset.id: scan.asset for scan in plan.scans})
    geometry: dict[str, tuple[str, tuple[float, float, float]]] = {}
    for link in plan.tooth_meshes:
        asset = assets.get(link.mesh_asset_id)
        if asset and asset.bounds:
            geometry[link.tooth.value] = (
                f"segmented-mesh-bounds:{asset.id}",
                _box_size_from_bounds(asset.bounds),
            )
    return geometry


def _box_size_from_bounds(bounds: BoundingBox) -> tuple[float, float, float]:
    sizes = [
        max(bounds.max_xyz[index] - bounds.min_xyz[index], 0.5)
        for index in range(3)
    ]
    return (sizes[0], sizes[1], sizes[2])


def _frame_to_stl(
    plan_id: str,
    stage_index: int,
    poses: list,
    tooth_geometry: dict,
) -> tuple[str, list[dict]]:
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    geometry_sources: list[dict] = []
    for index, pose in enumerate(poses):
        cx = (index % 8) * 4.0 + pose.translate_x_mm
        cy = (index // 8) * 5.0 + pose.translate_y_mm
        cz = pose.translate_z_mm
        source, size = tooth_geometry.get(
            pose.tooth.value,
            ("schematic-stage-proxy", (2.4, 3.2, 1.8)),
        )
        triangles.extend(_box_triangles(cx, cy, cz, *size))
        geometry_sources.append(
            {
                "tooth": pose.tooth.value,
                "source": source,
                "center_xyz_mm": [cx, cy, cz],
                "size_xyz_mm": list(size),
            }
        )
    return _stl_text(plan_id, stage_index, triangles), geometry_sources


def _stl_text(plan_id: str, stage_index: int, triangles: list) -> str:
    lines = [f"solid {plan_id}_stage_{stage_index:02d}"]
    for tri in triangles:
        lines.extend(
            [
                "  facet normal 0 0 0",
                "    outer loop",
                f"      vertex {tri[0][0]:.6f} {tri[0][1]:.6f} {tri[0][2]:.6f}",
                f"      vertex {tri[1][0]:.6f} {tri[1][1]:.6f} {tri[1][2]:.6f}",
                f"      vertex {tri[2][0]:.6f} {tri[2][1]:.6f} {tri[2][2]:.6f}",
                "    endloop",
                "  endfacet",
            ]
        )
    lines.append(f"endsolid {plan_id}_stage_{stage_index:02d}")
    return "\n".join(lines) + "\n"


def _box_triangles(cx: float, cy: float, cz: float, sx: float, sy: float, sz: float):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    tris = []
    for a, b, c, d in faces:
        tris.append((v[a], v[b], v[c]))
        tris.append((v[a], v[c], v[d]))
    return tris
