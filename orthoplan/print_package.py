from __future__ import annotations

import json
import zipfile
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan.hashing import canonical_json, sha256_bytes, sha256_text
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import review_tier_info
from orthoplan.print_aligner import write_aligner_shells
from orthoplan.print_manifest import write_manifest
from orthoplan.print_stl import build_tooth_geometry, frame_to_stl
from orthoplan.printing import PRINT_EXPORT_CAVEAT, build_print_export_status
from orthoplan.viz.progress import build_stage_progress_frames
from orthoplan.watermark import DataWatermark, content_bound_watermark


class PrintPackageResult(BaseModel):
    output_dir: str
    manifest_path: str
    artifact_paths: list[str] = Field(default_factory=list)
    artifact_sha256: dict[str, str] = Field(default_factory=dict)
    aligner_shell_paths: list[str] = Field(default_factory=list)
    aligner_shell_reports: list[dict] = Field(default_factory=list)
    aligner_shell_backend: dict = Field(default_factory=dict)
    manifest_sha256: str
    watermark_id: str
    review_tier: str = "stl-only"
    uses_real_mesh_geometry: bool = False
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
    workspace: str | Path | None = None,
) -> PrintPackageResult:
    """Generate stage STL files, a manifest, and optional zip/email draft.

    Stage geometry uses real per-tooth mesh vertices for *reviewed* segmentation
    links whose fragments resolve in ``workspace``; every other tooth falls back
    to a clearly-labeled schematic proxy box.
    """

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(plan.id)
    status = build_print_export_status(plan)
    frames = build_stage_progress_frames(plan)
    tooth_geometry = build_tooth_geometry(plan, workspace)
    plan_sha256, watermark = _plan_watermark(plan)
    artifacts, records = _write_stage_artifacts(output, frames, stem, tooth_geometry, watermark)
    shell_paths, shell_records, shell_reports, shell_backend = _export_shells(
        plan, output, frames, stem, tooth_geometry, watermark
    )
    manifest_path = write_manifest(
        plan, output, status, records, frames, stem, tooth_geometry,
        shell_records, shell_reports, shell_backend, watermark, plan_sha256,
    )
    zip_path, email_path = _bundle(
        plan, output, stem, status, manifest_path, artifacts, shell_paths,
        make_zip, make_email_draft,
    )
    return PrintPackageResult(
        output_dir=str(output),
        manifest_path=str(manifest_path),
        artifact_paths=artifacts,
        artifact_sha256={
            record["filename"]: record["sha256"] for record in (*records, *shell_records)
        },
        aligner_shell_paths=shell_paths,
        aligner_shell_reports=shell_reports,
        aligner_shell_backend=shell_backend,
        manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
        watermark_id=watermark.watermark_id,
        review_tier=review_tier_info(plan).tier.value,
        uses_real_mesh_geometry=any(g["mode"] == "mesh-vertices" for g in tooth_geometry.values()),
        zip_path=str(zip_path) if zip_path else None,
        zip_sha256=sha256_bytes(zip_path.read_bytes()) if zip_path else None,
        email_draft_path=str(email_path) if email_path else None,
    )


def _bundle(
    plan: TreatmentPlan,
    output: Path,
    stem: str,
    status,
    manifest_path: Path,
    artifacts: list[str],
    shell_paths: list[str],
    make_zip: bool,
    make_email_draft: bool,
) -> tuple[Path | None, Path | None]:
    zip_path = (
        _write_zip(
            stem, output,
            [manifest_path, *[Path(p) for p in artifacts], *[Path(p) for p in shell_paths]],
        )
        if make_zip
        else None
    )
    email_path = (
        _write_email_draft(plan, output, zip_path or manifest_path, status.delivery_email, stem)
        if make_email_draft
        else None
    )
    return zip_path, email_path


def _plan_watermark(plan: TreatmentPlan) -> tuple[str, DataWatermark]:
    """Plan content hash plus a watermark derived from it.

    Deterministic, not random: re-exporting an unchanged plan must produce
    byte-identical artifacts, so the watermark id is derived from plan content
    rather than freshly randomized on every call.
    """

    plan_payload = json.loads(plan_to_json(plan, indent=None))
    plan_sha256 = sha256_text(canonical_json(plan_payload))
    return plan_sha256, content_bound_watermark(f"{plan.id}:{plan_sha256}")


def _export_shells(
    plan: TreatmentPlan,
    output: Path,
    frames: list,
    stem: str,
    tooth_geometry: dict,
    watermark: DataWatermark,
) -> tuple[list[str], list[dict], list[dict], dict]:
    if not plan.settings.print_export.aligner_shell_enabled:
        return [], [], [], {}
    return write_aligner_shells(plan, output, frames, stem, tooth_geometry, watermark)


def _write_stage_artifacts(
    output: Path,
    frames: list,
    stem: str,
    tooth_geometry: dict,
    watermark: DataWatermark,
) -> tuple[list[str], list[dict]]:
    artifacts: list[str] = []
    records: list[dict] = []
    for frame in frames:
        path = output / f"{stem}-stage-{frame.stage_index:02d}-model.stl"
        stl, geometry_sources = frame_to_stl(
            stem,
            frame.stage_index,
            frame.poses,
            tooth_geometry,
            watermark,
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
