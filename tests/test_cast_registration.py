"""Exploratory registration preserves units and uses the stated transform direction."""
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("open3d")
from tools.cast_registration import rigid_fit, transform, trimmed_icp  # noqa: E402


def test_rigid_transform_direction_and_no_scale_even_with_scaled_input():
    rng = np.random.default_rng(21)
    source = rng.normal(size=(100, 3)) * [3, 2, 1]
    rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    target = source @ rotation.T + [20, -10, 5]
    matrix = rigid_fit(source, target)
    assert np.allclose(transform(source, matrix), target)
    assert np.allclose(transform(target, np.linalg.inv(matrix)), source)
    scaled_fit = rigid_fit(source, target * 1.1)
    assert np.allclose(scaled_fit[:3, :3].T @ scaled_fit[:3, :3], np.eye(3))
    assert np.linalg.det(scaled_fit[:3, :3]) == pytest.approx(1)
    assert not np.allclose(transform(source, scaled_fit), target * 1.1)


def test_trimmed_alignment_does_not_follow_unmatched_extreme_points():
    rng = np.random.default_rng(23)
    source = rng.uniform(-5, 5, (400, 3))
    target = source + [.05, -.08, .04]
    contaminated = np.vstack([source, rng.uniform(100, 200, (80, 3))])
    matrix, error = trimmed_icp(contaminated, target, np.eye(4), iterations=100)
    assert np.allclose(transform(source, matrix), target, atol=1e-5)
    assert error < 1e-8
