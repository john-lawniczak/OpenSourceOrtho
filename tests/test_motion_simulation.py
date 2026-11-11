import pytest
np = pytest.importorskip('numpy')
pytest.importorskip('scipy')
from orthoplan.longitudinal.simulation import posed_points, simulation_report, timing_profiles  # noqa: E402


def test_timing_is_monotone_preserves_endpoints_and_changes_interior():
    profiles = timing_profiles()
    for profile in profiles.values():
        fractions = profile['fractions']
        assert fractions[0] == 0 and fractions[-1] == 1
        assert np.all(np.diff(fractions) >= 0)
    assert profiles['smooth']['fractions'][1] < profiles['uniform']['fractions'][1]
    assert profiles['delayed']['fractions'][1] == 0


def test_proximity_detects_new_approach_without_claiming_intersection():
    face = np.array([[[0, 0, 0], [0, 1, 0], [0, 0, 1]]], dtype=float)
    mesh = np.concatenate([face, face+[2, 0, 0]])
    tooth = dict(pivot=[0, 0, 0], quaternion_xyzw=[0, 0, 0, 1])
    teeth = [{**tooth, 'tooth': '11', 'source_faces': [0], 'translation': [0, 0, 0]},
             {**tooth, 'tooth': '12', 'source_faces': [1], 'translation': [-2, 0, 0]}]
    report = simulation_report(mesh, teeth, threshold=.1)
    for profile in report['profiles'].values():
        assert profile['proximity_by_week'][0] == []
        end = profile['proximity_by_week'][-1]
        assert end[0]['new_proximity'] is True
        assert end[0]['sampled_distance'] == 0
        assert end[0]['baseline_distance'] == 2
    assert 'Absence does not establish clearance' in report['limitation']
    with pytest.raises(ValueError):
        simulation_report(mesh, teeth, threshold=-1)


def test_rigid_pose_preserves_shape_and_holds_unmatched_regions():
    points = np.random.default_rng(2).normal(size=(20, 3))
    tooth = dict(pivot=[1, 2, 3], translation=[.4, 0, 0], quaternion_xyzw=[0, 0, np.sin(.2), np.cos(.2)])
    moved = posed_points(points, tooth, .4)
    np.testing.assert_allclose(np.linalg.norm(np.diff(moved, axis=0), axis=1), np.linalg.norm(np.diff(points, axis=0), axis=1))
    np.testing.assert_allclose(posed_points(points, tooth, 0), points)
    tooth.update(translation=[0, 0, 0], quaternion_xyzw=[0, 0, 0, 1])
    np.testing.assert_allclose(posed_points(points, tooth, 1), points)
