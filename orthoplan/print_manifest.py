"""Print-package manifest assembly.

Split from ``print_package`` by responsibility: this module turns the pieces
produced by an export run (artifacts, shell records, findings, hashes) into
the ``*-print-manifest.json`` document; ``print_package`` owns orchestration,
zip/email packaging, and the STL/shell writers.
"""

from __future__ import annotations

import json
from pathlib import Path

from orthoplan import __version__
from orthoplan.evaluation.engine import run_rules
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import review_tier_info
from orthoplan.watermark import DataWatermark, watermark_block


def write_manifest(
    plan: TreatmentPlan,
    output: Path,
    status,
    artifacts: list[dict],
    frames: list,
    stem: str,
    tooth_geometry: dict,
    shell_records: list[dict],
    shell_reports: list[dict],
    shell_backend: dict,
    watermark: DataWatermark,
    plan_sha256: str,
) -> Path:
    findings = run_rules(plan)
    settings = plan.settings.print_export
    manifest = {
        "schema": "orthoplan-print-package-v2",
        "engine": {"name": "orthoplan", "version": __version__},
        "watermark": watermark_block(watermark),
        "plan_id": plan.id,
        "title": plan.title,
        "review_tier": review_tier_info(plan).model_dump(mode="json"),
        "uses_real_mesh_geometry": any(
            g["mode"] == "mesh-vertices" for g in tooth_geometry.values()
        ),
        "aligner_shells": _aligner_shell_block(
            settings, shell_records, shell_reports, shell_backend
        ),
        "hashes": _hashes_block(plan, plan_sha256, frames, findings, tooth_geometry, shell_records),
        "ready": status.ready,
        "blockers": status.blockers,
        "artifacts": artifacts,
        "delivery_email": status.delivery_email,
        "model_material": status.model_material,
        "thermoforming_material": status.thermoforming_material,
        "post_processing_notes": status.post_processing_notes,
        "printer_tolerances": status.printer_tolerances,
        "caveat": status.caveat,
    }
    path = output / f"{stem}-print-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _aligner_shell_block(
    settings, shell_records: list[dict], shell_reports: list[dict], shell_backend: dict
) -> dict:
    return {
        "enabled": settings.aligner_shell_enabled,
        "backend": shell_backend,
        "sheet_thickness_mm": settings.sheet_thickness_mm,
        "gingival_trim_margin_mm": settings.gingival_trim_margin_mm,
        "xy_compensation_mm": settings.xy_compensation_mm,
        "z_compensation_mm": settings.z_compensation_mm,
        "minimum_printable_feature_mm": settings.minimum_printable_feature_mm,
        "manufacturing_readiness": _manufacturing_readiness(
            settings.aligner_shell_enabled, shell_reports
        ),
        "artifacts": shell_records,
        "stage_reports": shell_reports,
    }


def _hashes_block(
    plan: TreatmentPlan,
    plan_sha256: str,
    frames: list,
    findings: list,
    tooth_geometry: dict,
    shell_records: list[dict],
) -> dict:
    return {
        "plan_sha256": plan_sha256,
        "stage_frames_sha256": sha256_text(canonical_json([f.model_dump() for f in frames])),
        "findings_sha256": sha256_text(canonical_json([f.model_dump(mode="json") for f in findings])),
        "scan_sha256": {scan.asset.id: scan.asset.sha256 for scan in plan.scans if scan.asset.sha256},
        "segmentation_fragment_sha256": _fragment_hashes(tooth_geometry),
        "aligner_shell_sha256": {record["filename"]: record["sha256"] for record in shell_records},
    }


def _fragment_hashes(tooth_geometry: dict) -> dict:
    return {
        geom["asset_id"]: geom["sha256"]
        for geom in tooth_geometry.values()
        if geom["mode"] == "mesh-vertices" and geom["sha256"]
    }


def _manufacturing_readiness(enabled: bool, reports: list[dict]) -> dict:
    if not enabled:
        return {
            "verdict": "NOT_APPLICABLE",
            "reason": "Aligner-shell export is disabled.",
        }
    if not reports or any(report["verdict"] == "ISSUES" for report in reports):
        return {
            "verdict": "ISSUES",
            "reason": "One or more shell stages could not produce consistent shell QA.",
        }
    if all(report["verdict"] == "NOT_APPLICABLE" for report in reports):
        return {
            "verdict": "NOT_APPLICABLE",
            "reason": "No reviewed real geometry was available for shell generation.",
        }
    return {
        "verdict": "CONSISTENT",
        "reason": "Generated shell artifacts passed available deterministic shell QA checks.",
    }
