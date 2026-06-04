"""3D-print package readiness and export.

This module describes export/package readiness and can generate simple printable
stage proxy STL files from the plan's current frame data. The generated files
are informational geometry outputs from the supplied plan, not a guarantee of
fit, safety, or suitability for any use.
"""

from __future__ import annotations

import json
import zipfile
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.model.plan import TreatmentPlan
from orthoplan.viz.progress import build_stage_progress_frames


PRINT_EXPORT_CAVEAT = (
    "Print export files are generated from the supplied plan data for informational use. "
    "Use, printing, materials, post-processing, and any physical application are the "
    "user's own responsibility and risk."
)


class PrintableArtifact(BaseModel):
    stage_index: int
    kind: str
    filename: str
    format: str
    note: str


class PrintExportStatus(BaseModel):
    enabled: bool
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    delivery_email: str | None = None
    model_material: str
    thermoforming_material: str
    post_processing_notes: str
    artifacts: list[PrintableArtifact] = Field(default_factory=list)
    caveat: str = PRINT_EXPORT_CAVEAT


class PrintPackageResult(BaseModel):
    output_dir: str
    manifest_path: str
    artifact_paths: list[str] = Field(default_factory=list)
    zip_path: str | None = None
    email_draft_path: str | None = None
    caveat: str = PRINT_EXPORT_CAVEAT


def build_print_export_status(plan: TreatmentPlan) -> PrintExportStatus:
    settings = plan.settings.print_export
    blockers: list[str] = []
    if not settings.enabled:
        blockers.append("print export is disabled")
    if not settings.safety_acknowledged:
        blockers.append("print/manufacturing safety acknowledgement is missing")
    if not plan.scale_confirmed:
        blockers.append("scan units must be confirmed before printer-scale export")
    if not (plan.data.segmented_teeth or plan.tooth_meshes):
        blockers.append("per-tooth segmentation or printable model geometry is unavailable")
    if not plan.stages:
        blockers.append("no staged plan exists to export")

    artifacts: list[PrintableArtifact] = []
    if settings.enabled and plan.stages:
        for stage in plan.stages:
            artifacts.append(
                PrintableArtifact(
                    stage_index=stage.index,
                    kind="dental-model",
                    filename=f"{plan.id}-stage-{stage.index:02d}-model.{settings.export_format}",
                    format=settings.export_format,
                    note="Stage proxy STL generated from current plan frame data.",
                )
            )

    return PrintExportStatus(
        enabled=settings.enabled,
        ready=not blockers,
        blockers=blockers,
        delivery_email=settings.delivery_email,
        model_material=settings.model_material,
        thermoforming_material=settings.thermoforming_material,
        post_processing_notes=settings.post_processing_notes,
        artifacts=artifacts,
    )


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
    status = build_print_export_status(plan)
    artifacts: list[str] = []

    for frame in build_stage_progress_frames(plan):
        path = output / f"{plan.id}-stage-{frame.stage_index:02d}-model.stl"
        path.write_text(_frame_to_stl(plan.id, frame.stage_index, frame.poses), encoding="utf-8")
        artifacts.append(str(path))

    manifest = {
        "plan_id": plan.id,
        "title": plan.title,
        "ready": status.ready,
        "blockers": status.blockers,
        "artifacts": [Path(path).name for path in artifacts],
        "delivery_email": status.delivery_email,
        "model_material": status.model_material,
        "thermoforming_material": status.thermoforming_material,
        "post_processing_notes": status.post_processing_notes,
        "caveat": status.caveat,
    }
    manifest_path = output / f"{plan.id}-print-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    zip_path = (
        _write_zip(plan.id, output, [manifest_path, *[Path(path) for path in artifacts]])
        if make_zip
        else None
    )
    email_path = (
        _write_email_draft(plan, output, zip_path or manifest_path, status.delivery_email)
        if make_email_draft
        else None
    )
    return PrintPackageResult(
        output_dir=str(output),
        manifest_path=str(manifest_path),
        artifact_paths=artifacts,
        zip_path=str(zip_path) if zip_path else None,
        email_draft_path=str(email_path) if email_path else None,
    )


def _write_zip(plan_id: str, output: Path, paths: list[Path]) -> Path:
    zip_path = output / f"{plan_id}-print-package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, arcname=path.name)
    return zip_path


def _write_email_draft(
    plan: TreatmentPlan,
    output: Path,
    attachment: Path,
    delivery_email: str | None,
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
    path = output / f"{plan.id}-print-package.eml"
    path.write_bytes(message.as_bytes())
    return path


def _frame_to_stl(plan_id: str, stage_index: int, poses: list) -> str:
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    for index, pose in enumerate(poses):
        cx = (index % 8) * 4.0 + pose.translate_x_mm
        cy = (index // 8) * 5.0 + pose.translate_y_mm
        cz = pose.translate_z_mm
        triangles.extend(_box_triangles(cx, cy, cz, 2.4, 3.2, 1.8))
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
