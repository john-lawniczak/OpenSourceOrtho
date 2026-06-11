from __future__ import annotations

import json
import zipfile
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field

from orthoplan import __version__
from orthoplan.evaluation.engine import run_rules
from orthoplan.hashing import canonical_json, sha256_bytes, sha256_text
from orthoplan.io.serialization import plan_to_json
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import review_tier_info
from orthoplan.print_aligner import write_aligner_shells
from orthoplan.print_stl import build_tooth_geometry, frame_to_stl
from orthoplan.printing import PRINT_EXPORT_CAVEAT, build_print_export_status
from orthoplan.viz.progress import build_stage_progress_frames


class PrintPackageResult(BaseModel):
    output_dir: str
    manifest_path: str
    artifact_paths: list[str] = Field(default_factory=list)
    artifact_sha256: dict[str, str] = Field(default_factory=dict)
    aligner_shell_paths: list[str] = Field(default_factory=list)
    manifest_sha256: str
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
    artifacts, records = _write_stage_artifacts(output, frames, stem, tooth_geometry)
    shell_paths: list[str] = []
    shell_records: list[dict] = []
    if plan.settings.print_export.aligner_shell_enabled:
        shell_paths, shell_records = write_aligner_shells(
            plan, output, frames, stem, tooth_geometry
        )
    manifest_path = _write_manifest(
        plan, output, status, records, frames, stem, tooth_geometry, shell_records
    )
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
    return PrintPackageResult(
        output_dir=str(output),
        manifest_path=str(manifest_path),
        artifact_paths=artifacts,
        artifact_sha256={
            record["filename"]: record["sha256"] for record in (*records, *shell_records)
        },
        aligner_shell_paths=shell_paths,
        manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
        review_tier=review_tier_info(plan).tier.value,
        uses_real_mesh_geometry=any(g["mode"] == "mesh-vertices" for g in tooth_geometry.values()),
        zip_path=str(zip_path) if zip_path else None,
        zip_sha256=sha256_bytes(zip_path.read_bytes()) if zip_path else None,
        email_draft_path=str(email_path) if email_path else None,
    )


def _write_stage_artifacts(
    output: Path,
    frames: list,
    stem: str,
    tooth_geometry: dict,
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
    tooth_geometry: dict,
    shell_records: list[dict],
) -> Path:
    plan_payload = json.loads(plan_to_json(plan, indent=None))
    findings = run_rules(plan)
    settings = plan.settings.print_export
    manifest = {
        "schema": "orthoplan-print-package-v2",
        "engine": {"name": "orthoplan", "version": __version__},
        "plan_id": plan.id,
        "title": plan.title,
        "review_tier": review_tier_info(plan).model_dump(mode="json"),
        "uses_real_mesh_geometry": any(
            g["mode"] == "mesh-vertices" for g in tooth_geometry.values()
        ),
        "aligner_shells": {
            "enabled": settings.aligner_shell_enabled,
            "sheet_thickness_mm": settings.sheet_thickness_mm,
            "gingival_trim_margin_mm": settings.gingival_trim_margin_mm,
            "artifacts": shell_records,
        },
        "hashes": {
            "plan_sha256": sha256_text(canonical_json(plan_payload)),
            "stage_frames_sha256": sha256_text(canonical_json([f.model_dump() for f in frames])),
            "findings_sha256": sha256_text(
                canonical_json([f.model_dump(mode="json") for f in findings])
            ),
            "scan_sha256": {
                scan.asset.id: scan.asset.sha256
                for scan in plan.scans
                if scan.asset.sha256
            },
            "segmentation_fragment_sha256": {
                geom["asset_id"]: geom["sha256"]
                for geom in tooth_geometry.values()
                if geom["mode"] == "mesh-vertices" and geom["sha256"]
            },
            "aligner_shell_sha256": {
                record["filename"]: record["sha256"] for record in shell_records
            },
        },
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


