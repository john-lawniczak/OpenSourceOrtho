import pytest
np = pytest.importorskip('numpy')
pytest.importorskip('scipy')
from orthoplan.longitudinal.projection import correspondence_mask  # noqa: E402
from orthoplan.longitudinal.registration import fit_sensitivity, reference_mesh  # noqa: E402
from orthoplan.longitudinal.rigid import fit_endpoint, transform  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402


def test_correspondence_rejects_distant_and_perpendicular_faces():
    base = np.array([[[x, 0, 0], [x+.1, 0, 0], [x, .1, 0]] for x in range(10)])
    target = base.copy()
    target[0] += [0, 0, 5]
    target[1, 2] = [1, 0, .1]
    nearest, valid, report = correspondence_mask(base, target, np.eye(4), max_distance=.2)
    assert not valid[0] and not valid[1] and valid[2:].all()
    assert report['accepted_fraction'] == .8
    assert np.array_equal(nearest[2:], np.arange(2, 10))


def test_fit_sensitivity_on_known_rigid_motion_and_reference_validation():
    points = np.random.default_rng(43).normal(size=(600, 3)) * [3, 2, 1]
    expected = np.eye(4)
    expected[:3, :3] = Rotation.from_euler('z', 4, degrees=True).as_matrix()
    expected[:3, 3] = [.1, -.1, .05]
    target = transform(points, expected)
    matrix, _ = fit_endpoint(points, target)
    report = fit_sensitivity(points, target, matrix)
    assert report['failed_trials'] == 0
    assert report['max_pivot_shift'] < 1e-5
    assert report['max_rotation_deg'] < 1e-5
    mesh = np.zeros((10, 3, 3))
    assert len(reference_mesh(mesh, list(range(6)))) == 6
    for faces in ([0], list(range(20)), [0.5]*6):
        with pytest.raises(ValueError):
            reference_mesh(mesh, faces)
