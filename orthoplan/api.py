"""Pure evaluation API shared by the CLI, the HTTP server, and tests.

This is the single place the UI (or any client) obtains findings, data gaps,
the timeline projection, and progress frames. It exists so the browser UI does
NOT reimplement the engine: the Python model is the only source of truth.

``evaluate_plan_payload`` is pure (dict in, dict out) and never raises on
invalid input - validation errors are returned as data so callers can surface
them instead of crashing.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from orthoplan.evaluation.acquisition import acquisition_advice
from orthoplan.evaluation.engine import run_rules
from orthoplan.evaluation.rules.root_bone import root_bone_review
from orthoplan.model.gaps import data_gap_actions, data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.review_tier import (
    cbct_handoff,
    cbct_status,
    registration_ready,
    review_tier_info,
)
from orthoplan.planning.biomechanics import movement_mode
from orthoplan.planning.optimizer import optimize_staging
from orthoplan.planning.timeline import project_timeline
from orthoplan.printing import build_print_export_status, export_print_package
from orthoplan.viz.progress import build_stage_progress_frames


def _format_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "(plan)"
        messages.append(f"{location}: {item.get('msg', 'invalid')}")
    return messages


def evaluate_plan(plan: TreatmentPlan) -> dict[str, Any]:
    """Evaluate a validated plan with the canonical engine."""

    findings = run_rules(plan)
    frames = build_stage_progress_frames(plan)
    timeline = project_timeline(plan)
    optimized = optimize_staging(plan)
    return {
        "ok": True,
        "scale_confirmed": plan.scale_confirmed,
        "review_tier": review_tier_info(plan).model_dump(mode="json"),
        "cbct_status": cbct_status(plan).value,
        "cbct_handoff": cbct_handoff(plan).model_dump(mode="json"),
        "registration": {
            "ready": registration_ready(plan),
            "transforms": [reg.model_dump(mode="json") for reg in plan.registrations],
        },
        "derived_anatomy": _derived_anatomy_block(plan),
        "root_bone_review": {"verdict": root_bone_review(plan).verdict.value},
        "movement_model": movement_mode(plan),
        "data_gaps": data_gaps(plan),
        "data_gap_actions": [action.model_dump() for action in data_gap_actions(plan)],
        "acquisition_advice": acquisition_advice(plan).model_dump(),
        "findings": [finding.model_dump() for finding in findings],
        "timeline": timeline.model_dump(),
        "print_export": build_print_export_status(plan).model_dump(),
        "clinical_controls": _clinical_controls_block(plan),
        "optimized_staging": {
            "stage_count": len(optimized.plan.stages),
            "issues": [issue.model_dump() for issue in optimized.issues],
            "plan": optimized.plan.model_dump(mode="json"),
            "caveat": optimized.caveat,
        },
        "render_meshes": [
            {
                "tooth": link.tooth.value,
                "mesh_asset_id": link.mesh_asset_id,
                "url": f"/api/mesh/{link.mesh_asset_id}",
                "source": link.source.value,
            }
            for link in plan.tooth_meshes
        ],
        "frames": [frame.ui_dict() for frame in frames],
        # Approximate per-tooth frames (keyed by FDI value) for a 3D viewer to
        # orient rotation. Empty unless segmentation supplied local frames.
        "tooth_frames": {
            link.tooth.value: link.local_frame.model_dump()
            for link in plan.tooth_meshes
            if link.local_frame is not None
        },
    }


def _clinical_controls_block(plan: TreatmentPlan) -> dict[str, Any]:
    return {
        "attachments": [attachment.model_dump(mode="json") for attachment in plan.attachments],
        "interproximal_reductions": [
            ipr.model_dump(mode="json") for ipr in plan.interproximal_reductions
        ],
        "planned_spacing": [spacing.model_dump(mode="json") for spacing in plan.planned_spacing],
        "fixed_teeth": [fixed.model_dump(mode="json") for fixed in plan.fixed_teeth],
        "movement_exclusions": [
            exclusion.model_dump(mode="json") for exclusion in plan.movement_exclusions
        ],
    }


def _derived_anatomy_block(plan: TreatmentPlan) -> dict[str, Any] | None:
    """Reviewed CBCT-derived anatomy with per-object trust flags, or None.

    ``trusted`` (reviewed AND in field) is computed here so the UI never has to
    re-derive the fail-closed rule.
    """

    anatomy = plan.derived_anatomy
    if anatomy is None:
        return None

    def _row(obj: Any) -> dict[str, Any]:
        data = obj.model_dump(mode="json")
        data["trusted"] = obj.trusted
        data["reviewed"] = obj.reviewed
        return data

    return {
        "has_trusted": anatomy.has_trusted,
        "roots": [_row(r) for r in anatomy.roots],
        "tooth_axes": [_row(a) for a in anatomy.tooth_axes],
        "alveolar_bone": [_row(b) for b in anatomy.alveolar_bone],
    }


def evaluate_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw plan payload and evaluate it. Never raises."""

    try:
        plan = TreatmentPlan.model_validate(payload)
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}
    return evaluate_plan(plan)


def print_package_payload(
    payload: dict[str, Any], *, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Validate a plan and build a downloadable print package. Never raises.

    Reuses :func:`export_print_package` (stage proxy STLs + manifest + zip + an
    ``.eml`` draft that already embeds the zip as an attachment) and returns the
    artifacts base64-encoded so the JSON-only dev server can hand them to the
    browser for download / emailing. The ``.eml`` opens in a mail client with the
    files pre-attached, which is the "email it to yourself / attach it" path.
    """

    try:
        plan = TreatmentPlan.model_validate(payload)
    except ValidationError as exc:
        return {"ok": False, "errors": _format_errors(exc)}

    status = build_print_export_status(plan)
    if not status.ready:
        return {
            "ok": False,
            "errors": status.blockers,
            "print_export": status.model_dump(mode="json"),
        }
    with tempfile.TemporaryDirectory() as tmp:
        result = export_print_package(
            plan, tmp, make_zip=True, make_email_draft=True, workspace=workspace
        )
        zip_path = Path(result.zip_path) if result.zip_path else None
        eml_path = Path(result.email_draft_path) if result.email_draft_path else None
        zip_bytes = zip_path.read_bytes() if zip_path else b""
        eml_bytes = eml_path.read_bytes() if eml_path else b""
        zip_name = zip_path.name if zip_path else "print-package.zip"
        eml_name = eml_path.name if eml_path else "print-package.eml"

    return {
        "ok": True,
        "filename": zip_name,
        "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
        "zip_sha256": result.zip_sha256,
        "email_filename": eml_name,
        "email_eml_base64": base64.b64encode(eml_bytes).decode("ascii"),
        "delivery_email": status.delivery_email,
        "stage_count": len(result.artifact_paths),
        "review_tier": result.review_tier,
        "uses_real_mesh_geometry": result.uses_real_mesh_geometry,
        "aligner_shell_count": len(result.aligner_shell_paths),
        "aligner_shell_reports": result.aligner_shell_reports,
        "aligner_shell_backend": result.aligner_shell_backend,
        "manufacturing_readiness": status.manufacturing_readiness,
        "printer_tolerances": status.printer_tolerances,
        "caveat": result.caveat,
    }
