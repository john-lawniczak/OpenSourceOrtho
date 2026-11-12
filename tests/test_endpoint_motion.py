"""Endpoint fitting recovers known geometry, without asserting anatomical truth."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from scipy.spatial.transform import Rotation  # noqa: E402

from orthoplan.longitudinal.matching import assign_regions, tooth_motion  # noqa: E402
from orthoplan.longitudinal.projection import project_regions  # noqa: E402
from orthoplan.longitudinal.rigid import (  # noqa: E402
    fit_endpoint, rigid_fit, surface_points, transform, trimmed_icp,
)


def known_transform():
    matrix = np.eye(4)
    matrix[:3, :3] = Rotation.from_euler("xyz", [2, -3, 5], degrees=True).as_matrix()
    matrix[:3, 3] = [0.12, -0.08, 0.06]
    return matrix


def cloud():
    return np.random.default_rng(17).normal(size=(500, 3)) * [1.4, 0.9, 0.6]


def test_paired_rigid_fit_recovers_rotation_translation_without_scale_or_reflection():
    points, expected = cloud(), known_transform()
    np.testing.assert_allclose(rigid_fit(points, transform(points, expected)), expected, atol=1e-10)
    reflected = points * [-1, 1, 1]
    assert np.linalg.det(rigid_fit(points, reflected)[:3, :3]) == pytest.approx(1)
    with pytest.raises(ValueError, match="Collinear"):
        rigid_fit(np.zeros((10, 3)), np.zeros((10, 3)))


def test_icp_recovers_known_small_motion_with_target_outliers():
    points, expected = cloud(), known_transform()
    target = np.concatenate([transform(points, expected), [[50, 40, 30], [45, 44, 40]]])
    fitted, metrics = trimmed_icp(points, target)
    np.testing.assert_allclose(fitted, expected, atol=1e-5)
    assert metrics["median_residual"] < 1e-5
    with pytest.raises(ValueError, match="finite"):
        trimmed_icp(points * np.nan, target)


def test_identity_surface_has_no_invented_motion():
    points = cloud()
    matrix, metrics = fit_endpoint(points, points.copy())
    np.testing.assert_allclose(matrix, np.eye(4), atol=1e-10)
    assert metrics["p90_residual"] < 1e-10


def test_correspondence_uses_geometry_not_independent_fdi_names():
    a = {"points": cloud(), "tooth": "11"}
    b = {"points": cloud() + [10, 0, 0], "tooth": "12"}
    # Reordered and differently named target drafts must not swap physical regions.
    target = [{**b, "tooth": "11"}, {**a, "tooth": "12"}]
    assert assign_regions([a, b], target, np.eye(4)) == {0: 1, 1: 0}


def test_weak_segmentation_still_produces_preview_and_missing_match_is_held():
    points, expected = cloud(), known_transform()
    region = {"points": points, "tooth": "11", "faces": np.arange(10), "confidence": 0.25}
    target = {"points": transform(points, expected), "tooth": "11", "confidence": 0.25,
              "independent_label": "12"}
    motion = tooth_motion(region, target, np.eye(4))
    assert motion["status"] == "estimated-weak"
    assert motion["reviewed"] is False
    pivot = np.array(motion["pivot"])
    np.testing.assert_allclose(motion["translation"], transform(pivot, expected) - pivot, atol=1e-5)
    np.testing.assert_allclose(Rotation.from_quat(motion["quaternion_xyzw"]).as_matrix(),
                               expected[:3, :3], atol=1e-5)
    held = tooth_motion(region, None, np.eye(4))
    assert held["status"] == "held-unmatched"
    assert held["translation"] == [0, 0, 0]


def test_projected_masks_are_disjoint_and_leave_context_unassigned():
    rng = np.random.default_rng(2)
    source = rng.normal(size=(80, 3, 3))
    regions = [dict(tooth="11", faces=np.arange(0, 30), confidence=0.4),
               dict(tooth="12", faces=np.arange(30, 60), confidence=0.4)]
    projected = project_regions(source, source.copy(), regions, np.eye(4), regions, {0: 0, 1: 1})
    assert [r["face_count"] for r in projected] == [30, 30]
    for i, item in enumerate(projected):
        np.testing.assert_allclose(item["points"], surface_points(source[regions[i]["faces"]]))


def test_degenerate_tooth_region_is_held_without_blocking_other_estimates():
    region = {"points": np.zeros((20, 3)), "tooth": "11", "faces": np.arange(10), "confidence": 0.2}
    target = {**region}
    held = tooth_motion(region, target, np.eye(4))
    assert held["status"] == "held-unmatched"
    assert held["fit"] is None
    assert held["translation"] == [0, 0, 0]


def test_projected_correspondence_and_local_fit_recover_motion_in_shared_frame():
    rng = np.random.default_rng(24)
    first = rng.normal(size=(300, 3, 3)) * [1.4, 0.9, 0.6]
    second = first + [12, 0, 0]
    source = np.concatenate([first, second])
    tooth_delta = known_transform()
    registered_target = np.concatenate([transform(first, tooth_delta), second])
    # Model a separate scanner pose; the local fitter must apply registration once.
    registration = np.eye(4)
    registration[:3, 3] = [2, -3, 1]
    target = transform(registered_target, np.linalg.inv(registration))
    regions = [dict(tooth=tooth, faces=np.arange(i * 300, (i + 1) * 300),
                    confidence=0.3, points=surface_points(mesh, 1600))
               for i, (tooth, mesh) in enumerate([("11", first), ("12", second)])]
    # Random triangle soup has no coherent surface normals. Test frame composition
    # independently of normal rejection (covered with physical patches separately).
    projected = project_regions(source, target, regions, registration, regions, {0: 0, 1: 1},
                                thresholds={"min_normal": 0})
    moved = tooth_motion(regions[0], projected[0], registration)
    pivot = np.array(moved["pivot"])
    np.testing.assert_allclose(moved["translation"], transform(pivot, tooth_delta) - pivot, atol=1e-5)
    stationary = tooth_motion(regions[1], projected[1], registration)
    np.testing.assert_allclose(stationary["translation"], [0, 0, 0], atol=1e-5)
