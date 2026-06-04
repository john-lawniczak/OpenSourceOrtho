"""3D-print handoff readiness.

This module describes export/package readiness for clinician-supervised model
printing and thermoforming workflows. It does not generate clinical aligners or
claim the output is treatment-ready.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orthoplan.model.plan import TreatmentPlan


PRINT_EXPORT_CAVEAT = (
    "Print export metadata is for clinician-supervised dental model/thermoforming "
    "workflows only. It is not authorization to manufacture or wear aligners."
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
                    note="Planned model artifact metadata; mesh generation/export is a future step.",
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
