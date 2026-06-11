"""3D-print package readiness and export.

This module describes export/package readiness and can generate simple printable
stage proxy STL files from the plan's current frame data. The generated files
are informational geometry outputs from the supplied plan, not a guarantee of
fit, safety, or suitability for any use.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.plan import TreatmentPlan


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
    manufacturing_readiness: dict[str, str]
    artifacts: list[PrintableArtifact] = Field(default_factory=list)
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
        manufacturing_readiness=_manufacturing_readiness(plan, blockers),
        artifacts=artifacts,
    )


def _manufacturing_readiness(plan: TreatmentPlan, blockers: list[str]) -> dict[str, str]:
    settings = plan.settings.print_export
    if not settings.aligner_shell_enabled:
        return {
            "verdict": "NOT_APPLICABLE",
            "reason": "Aligner-shell export is disabled.",
        }
    if blockers:
        return {
            "verdict": "ISSUES",
            "reason": "Print export prerequisites are incomplete.",
        }
    if not any(link.reviewed for link in plan.tooth_meshes):
        return {
            "verdict": "NOT_APPLICABLE",
            "reason": "Reviewed real tooth geometry is unavailable; model-only export remains available.",
        }
    return {
        "verdict": "CONSISTENT",
        "reason": "Reviewed tooth geometry is present; package export will run deterministic shell QA.",
    }


from orthoplan.print_package import PrintPackageResult, export_print_package  # noqa: E402
