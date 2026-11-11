"""Feasible one-to-one region assignment and explicit alternative-match evidence."""

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from orthoplan.longitudinal.rigid import transform

MAX_NORMALIZED_DISTANCE = 1.5
AMBIGUITY_COST_MARGIN = 0.05


def feasible_assignment(costs, feasible):
    """Maximize feasible match count, then minimize cost; unmatched rows are explicit.

    Invalid edges never participate. Filtering an unconstrained assignment after
    optimization can discard a valid match that an invalid edge displaced.
    """
    costs, feasible = np.asarray(costs, dtype=float), np.asarray(feasible, dtype=bool)
    if (
        costs.ndim != 2
        or feasible.shape != costs.shape
        or not np.isfinite(costs).all()
        or np.any(costs < 0)
    ):
        raise ValueError(
            "Expected finite nonnegative assignment costs and a matching feasibility mask"
        )
    n, m = costs.shape
    if not n or not m:
        return {}
    unmatched = (float(costs[feasible].max()) + 1) * (n + 1) if feasible.any() else 1
    augmented = np.full((n, m + n), unmatched, dtype=float)
    augmented[:, :m] = np.where(feasible, costs, np.inf)
    rows, columns = linear_sum_assignment(augmented)
    return {int(i): int(j) for i, j in zip(rows, columns) if j < m}


def assignment_diagnostics(costs, feasible, assignment, target_ids):
    total = sum(costs[i, j] for i, j in assignment.items())
    evidence = []
    for i in range(len(costs)):
        candidates = sorted(np.flatnonzero(feasible[i]), key=lambda j: costs[i, j])
        row = {
            "candidate_count": len(candidates),
            "ambiguous": False,
            "alternative_cost_increase": None,
            "ambiguity_cost_margin": AMBIGUITY_COST_MARGIN,
            "candidates": [
                {"target_tooth": target_ids[j], "cost": float(costs[i, j])} for j in candidates[:3]
            ],
            "interpretation": "Normalized geometric assignment costs; not identity probabilities",
        }
        if i not in assignment:
            row["status"] = (
                "unmatched-no-feasible-region" if not candidates else "unmatched-competing-regions"
            )
        else:
            j = assignment[i]
            alternative_mask = feasible.copy()
            alternative_mask[i, j] = False
            alternative = feasible_assignment(costs, alternative_mask)
            row.update(
                status="assigned-draft",
                target_tooth=target_ids[j],
                assigned_cost=float(costs[i, j]),
            )
            if len(alternative) == len(assignment):
                margin = max(0.0, float(sum(costs[a, b] for a, b in alternative.items()) - total))
                row.update(
                    alternative_cost_increase=margin, ambiguous=margin <= AMBIGUITY_COST_MARGIN
                )
        evidence.append(row)
    return evidence


def region_assignment(source, target, registration):
    if not source or not target:
        return {}, []
    a = [r["points"] for r in source]
    b = [transform(r["points"], registration) for r in target]
    size_a = np.array([max(np.linalg.norm(np.ptp(p, axis=0)), 1e-9) for p in a])
    size_b = np.array([max(np.linalg.norm(np.ptp(p, axis=0)), 1e-9) for p in b])
    distances = cdist([p.mean(axis=0) for p in a], [p.mean(axis=0) for p in b]) / size_a[:, None]
    costs = distances + 0.25 * np.abs(np.log(size_a[:, None] / size_b[None, :]))
    feasible = distances <= MAX_NORMALIZED_DISTANCE
    assignment = feasible_assignment(costs, feasible)
    return assignment, assignment_diagnostics(
        costs, feasible, assignment, [r["tooth"] for r in target]
    )
