import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from orthoplan.longitudinal.contact_detail import surface_distance  # noqa: E402


def test_crossing_triangle_interiors_are_detected_when_vertices_are_far_apart():
    left = np.array([[[-10, -10, 0], [10, -10, 0], [0, 10, 0]]], dtype=float)
    right = np.array([[[0, 0, -10], [0, 0, 10], [0, 2, 0]]], dtype=float)
    report = surface_distance(left, right)
    assert report["status"] == "complete" and report["distance"] == 0
    assert report["surface_contact_or_intersection"]
    separated = surface_distance(left, left + [0, 0, 3])
    assert separated["distance"] == pytest.approx(3)
    incomplete = surface_distance(left, right, max_tests=0)
    assert incomplete["status"] == "indeterminate" and incomplete["distance"] is None


def test_incomplete_full_surface_shell_check_downgrades_report(monkeypatch):
    from orthoplan.aligner_shell import build_aligner_shell
    from orthoplan.print_aligner import _failed_checks

    monkeypatch.setattr(
        "orthoplan.aligner_shell.surface_distance",
        lambda *a, **kw: {"status": "indeterminate", "distance": None},
    )
    shell = build_aligner_shell([((0, 0, 0), (1, 0, 0), (0, 1, 0))], thickness_mm=0.8)
    assert shell.stats.inner_outer_surface_clearance_mm is None
    assert "full-surface clearance check incomplete" in _failed_checks(shell.stats)
