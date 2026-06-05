"""Arithmetic timeline projection.

This is deliberately not a completion estimate. It multiplies the stage count by
the configured wear interval and reports the result with a standing caveat. No
duration is stored on the plan; it is computed on demand from inputs only.
"""

from __future__ import annotations

from pydantic import BaseModel

from orthoplan.model.plan import TreatmentPlan

PROJECTION_CAVEAT = (
    "Projection excludes refinements, compliance variation, pauses, "
    "and user-directed changes."
)


class TimelineProjection(BaseModel):
    stage_count: int
    wear_interval_days: int
    projected_duration_days: int
    projected_duration_weeks: float
    caveat: str = PROJECTION_CAVEAT


def project_timeline(plan: TreatmentPlan) -> TimelineProjection:
    stage_count = len(plan.stages)
    wear_interval_days = plan.settings.timeline.wear_interval_days
    days = stage_count * wear_interval_days
    return TimelineProjection(
        stage_count=stage_count,
        wear_interval_days=wear_interval_days,
        projected_duration_days=days,
        projected_duration_weeks=round(days / 7, 1),
    )
