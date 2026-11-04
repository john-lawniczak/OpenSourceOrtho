"""Broad-phase bounds must enclose the same root-aware motion as surfaces."""
from types import SimpleNamespace

from orthoplan.evaluation.rules.contact_geometry import staged_contact_candidates
from orthoplan.model import BoundingBox, TreatmentPlan


def test_rotated_contact_is_not_pruned_by_unrotated_bounds(monkeypatch):
    plan = TreatmentPlan.model_validate({"id": "rotation", "stages": [{"index": 0, "deltas": [
        {"tooth": {"value": "11"}, "rotate_rotation_deg": 90},
    ]}]})
    frame = SimpleNamespace(axis=SimpleNamespace(direction=(0, 0, 1)), center_of_resistance=(0, 0, 0))
    monkeypatch.setattr('orthoplan.evaluation.rules.contact_geometry.trusted_movement_frames', lambda plan: {"11": frame})
    bounds = {
        "11": BoundingBox(min_xyz=(2, 0, -.1), max_xyz=(4, 1, .1)),
        "21": BoundingBox(min_xyz=(-.8, 2.5, -.1), max_xyz=(-.2, 3, .1)),
    }
    result = staged_contact_candidates(plan, bounds)
    assert ("11", "21") in result
    assert result[("11", "21")].bbox_overlap_mm > 0
