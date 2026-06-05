"""Deterministic rule aggregator.

`run_rules` is the single place that knows which deterministic rules exist, so
the api, CLI, and tests all evaluate the same set. New deterministic rules are
registered here.
"""

from __future__ import annotations

from orthoplan.evaluation.finding import Finding
from orthoplan.evaluation.rules.clinical_controls import evaluate_clinical_controls
from orthoplan.evaluation.rules.collisions import evaluate_segmented_mesh_collisions
from orthoplan.evaluation.rules.mesh_quality import evaluate_mesh_quality
from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.evaluation.rules.plan_checks import (
    evaluate_no_movement,
    evaluate_root_sensitive_movement,
    evaluate_segmentation_presence,
)
from orthoplan.model.plan import TreatmentPlan

_RULES = (
    evaluate_movement_caps,
    evaluate_clinical_controls,
    evaluate_segmented_mesh_collisions,
    evaluate_mesh_quality,
    evaluate_root_sensitive_movement,
    evaluate_segmentation_presence,
    evaluate_no_movement,
)


def run_rules(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    for rule in _RULES:
        findings.extend(rule(plan))
    return findings
