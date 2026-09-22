"""Offline 'local helper' review that acts on user notes deterministically.

When no external model is connected (the default), the Generate Plan pipeline
still needs to *act on* the user's notes rather than drop them. This produces a
deterministic, linted educational finding that reflects the user's focus back and
relates it to what the generated plan actually does (which teeth move, and by how
much). It is not a remote model and does not reason freely - it is honest,
offline acknowledgement that routes the user to a professional.

Output is MODEL-provenance and passes the same `lint_finding` gate as remote
advisories, so it renders with the `[ADVISORY - unverified]` prefix and cannot
carry verdict language or mechanics findings.
"""

from __future__ import annotations

from math import hypot

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    quarantine_findings,
)
from orthoplan.model.plan import TreatmentPlan

_AXES = ("translate_x_mm", "translate_y_mm", "translate_z_mm")


def _top_movements(plan: TreatmentPlan, limit: int = 6) -> list[tuple[str, float]]:
    totals: dict[str, list[float]] = {}
    for stage in plan.stages:
        for delta in stage.deltas:
            bucket = totals.setdefault(delta.tooth.value, [0.0, 0.0, 0.0])
            for i, axis in enumerate(_AXES):
                bucket[i] += getattr(delta, axis)
    magnitudes = {t: hypot(v[0], v[1], v[2]) for t, v in totals.items()}
    ranked = sorted(magnitudes.items(), key=lambda kv: kv[1], reverse=True)
    return [(t, round(m, 3)) for t, m in ranked if m > 0][:limit]


def local_notes_advisory(plan: TreatmentPlan, notes: str) -> list[Finding]:
    """Return linted educational finding(s) that act on the user's notes offline."""

    note = notes.strip()
    if not note:
        return []

    movements = _top_movements(plan)
    moved = ", ".join(f"FDI {t} {m} mm" for t, m in movements) if movements else "no net tooth movement"
    message = (
        f'You asked this review to focus on: "{note}". This generated plan is a '
        f"deterministic, educational proposal; its largest planned tooth movements are: "
        f"{moved}. Compare that with your focus and confirm with a dental professional "
        "whether it addresses your concern - the local helper cannot judge suitability."
    )
    finding = Finding(
        severity=FindingSeverity.INFO,
        category=FindingCategory.EDUCATION,
        provenance=FindingProvenance.MODEL,
        title="Your focus note was reviewed (local helper)",
        message=message,
        clinician_question="Does the planned movement match the focus you described, and is it appropriate?",
    )
    accepted, _ = quarantine_findings([finding])
    return accepted
