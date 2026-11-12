"""Missing regions and nearly interchangeable assignments must not masquerade as identity."""

import itertools
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from orthoplan.longitudinal.correspondence import feasible_assignment, assignment_diagnostics  # noqa: E402
from orthoplan.longitudinal.matching import tooth_motion  # noqa: E402


def test_invalid_candidate_cannot_displace_the_better_valid_match():
    costs = np.array([[0.1, 1.6], [0.15, 2.0]])
    feasible = np.array([[True, False], [True, False]])
    assert feasible_assignment(costs, feasible) == {0: 0}
    assert feasible_assignment(np.ones((2, 2)), np.zeros((2, 2), dtype=bool)) == {}


def test_feasible_assignment_matches_exhaustive_small_graph_optimum():
    rng = np.random.default_rng(5)
    for _ in range(30):
        costs = rng.uniform(0, 3, (3, 2))
        feasible = rng.random((3, 2)) > 0.4
        scored = []
        for choices in itertools.product([None, 0, 1], repeat=3):
            pairs = {i: j for i, j in enumerate(choices) if j is not None}
            if len(set(pairs.values())) != len(pairs) or any(
                not feasible[i, j] for i, j in pairs.items()
            ):
                continue
            scored.append((-len(pairs), sum(costs[i, j] for i, j in pairs.items())))
        result = feasible_assignment(costs, feasible)
        assert (-len(result), sum(costs[i, j] for i, j in result.items())) == min(scored)


def test_alternative_assignment_evidence_distinguishes_ties_and_separation():
    feasible = np.ones((2, 2), dtype=bool)
    tied = np.ones((2, 2))
    rows = assignment_diagnostics(tied, feasible, feasible_assignment(tied, feasible), ["11", "12"])
    assert all(r["ambiguous"] and r["alternative_cost_increase"] == 0 for r in rows)
    separated = np.array([[0.1, 1], [1, 0.1]])
    rows = assignment_diagnostics(
        separated, feasible, feasible_assignment(separated, feasible), ["11", "12"]
    )
    assert all(
        not r["ambiguous"] and r["alternative_cost_increase"] == pytest.approx(1.8) for r in rows
    )


def test_ambiguous_identity_flags_a_good_surface_fit_without_disabling_preview():
    points = np.random.default_rng(4).normal(size=(100, 3))
    source = dict(tooth="11", points=points, faces=np.arange(20), confidence=0.5)
    target = {**source, "assignment_evidence": {"ambiguous": True}}
    motion = tooth_motion(source, target, np.eye(4))
    assert motion["status"] == "estimated-weak"
    assert motion["fit"]["p90_residual"] < 1e-10
    assert motion["assignment_evidence"]["ambiguous"]
    assert motion["reviewed"] is False
