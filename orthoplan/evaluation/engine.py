"""Deterministic rule aggregator.

`run_rules` is the single place that knows which deterministic rules exist, so
the api, CLI, and tests all evaluate the same set. New deterministic rules are
registered here.
"""

from __future__ import annotations

from orthoplan.evaluation.finding import Finding
from orthoplan.evaluation.rules.mesh_quality import evaluate_mesh_quality
from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.model.plan import TreatmentPlan

_RULES = (evaluate_movement_caps, evaluate_mesh_quality)


def run_rules(plan: TreatmentPlan) -> list[Finding]:
    findings: list[Finding] = []
    for rule in _RULES:
        findings.extend(rule(plan))
    return findings
