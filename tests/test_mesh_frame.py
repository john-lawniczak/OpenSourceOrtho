from __future__ import annotations

from orthoplan.planning.mesh_frame import compute_local_frame


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_principal_axis_aligns_with_max_variance_direction() -> None:
    # A point cloud stretched along x: the first PCA axis should be ~x.
    vertices = [(t, 0.0, 0.0) for t in (-3.0, -1.0, 0.0, 1.0, 3.0)]
    vertices += [(0.0, 0.2, 0.0), (0.0, -0.2, 0.0)]
    frame = compute_local_frame(vertices)
    assert frame is not None
    assert abs(_dot(frame.axes[0], (1.0, 0.0, 0.0))) > 0.95  # aligned (sign-agnostic)
    assert frame.approximate is True
    assert frame.source == "pca-crown"


def test_axes_are_unit_length_and_ordered_by_variance() -> None:
    vertices = [
        (2.0, 0.0, 0.0), (-2.0, 0.0, 0.0),  # large variance x
        (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),  # medium variance y
        (0.0, 0.0, 0.2), (0.0, 0.0, -0.2),  # small variance z
    ]
    frame = compute_local_frame(vertices)
    assert frame is not None
    for axis in frame.axes:
        assert abs((axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2) ** 0.5 - 1.0) < 1e-9
    assert abs(_dot(frame.axes[0], (1.0, 0.0, 0.0))) > 0.95
    assert abs(_dot(frame.axes[2], (0.0, 0.0, 1.0))) > 0.95


def test_degenerate_cloud_yields_no_frame() -> None:
    assert compute_local_frame([(1.0, 1.0, 1.0)] * 5) is None
    assert compute_local_frame([(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]) is None  # < 3 points
