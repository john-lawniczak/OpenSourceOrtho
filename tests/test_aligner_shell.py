from __future__ import annotations

import pytest

from orthoplan.aligner_shell import TrimPlane, build_aligner_shell

# A flat quad surface (two triangles, +z winding). Offsetting it and stitching the
# rim must produce a closed slab of the requested thickness.
_QUAD = [
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)),
    ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
]

_INVERTED_QUAD = [(tri[0], tri[2], tri[1]) for tri in _QUAD]


def test_shell_is_watertight_and_has_requested_thickness() -> None:
    result = build_aligner_shell(_QUAD, thickness_mm=0.6)
    assert result.stats.watertight is True
    assert result.stats.measured_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.min_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.p50_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.max_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.connected_components == 1
    # 2 outer + 2 inner + 4 boundary edges x 2 rim triangles = 12.
    assert result.stats.triangle_count == 12


def test_zero_or_negative_thickness_is_rejected() -> None:
    with pytest.raises(ValueError, match="thickness"):
        build_aligner_shell(_QUAD, thickness_mm=0.0)


def test_empty_surface_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        build_aligner_shell([], thickness_mm=0.5)


def test_degenerate_input_triangles_are_dropped_before_shelling() -> None:
    degenerate = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))

    result = build_aligner_shell([degenerate, *_QUAD], thickness_mm=0.5)

    assert result.stats.dropped_degenerate_input_triangles == 1
    assert result.stats.watertight is True


def test_inverted_winding_is_oriented_before_shelling() -> None:
    result = build_aligner_shell(_INVERTED_QUAD, thickness_mm=0.5)

    assert result.stats.watertight is True
    assert result.stats.connected_components == 1


def test_disconnected_islands_are_reported() -> None:
    shifted = [
        tuple((v[0] + 5.0, v[1], v[2]) for v in tri)  # type: ignore[misc]
        for tri in _QUAD
    ]

    result = build_aligner_shell([*_QUAD, *shifted], thickness_mm=0.5)

    assert result.stats.connected_components == 2


def test_skinny_input_triangles_are_reported() -> None:
    skinny = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.000001, 0.0))

    result = build_aligner_shell([skinny, *_QUAD], thickness_mm=0.5)

    assert result.stats.skinny_input_triangle_count == 1


def test_all_degenerate_input_fails_closed() -> None:
    degenerate = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))

    with pytest.raises(ValueError, match="non-empty"):
        build_aligner_shell([degenerate], thickness_mm=0.5)


def _strip() -> list:
    a, b = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
    c, d = (0.0, 5.0, 0.0), (1.0, 5.0, 0.0)
    e, f = (0.0, 10.0, 0.0), (1.0, 10.0, 0.0)
    return [(a, b, d), (a, d, c), (c, d, f), (c, f, e)]


def test_compensation_defaults_to_no_geometry_change() -> None:
    baseline = build_aligner_shell(_QUAD, thickness_mm=0.6)
    compensated = build_aligner_shell(
        _QUAD, thickness_mm=0.6, xy_compensation_mm=0.0, z_compensation_mm=0.0
    )
    assert compensated.triangles == baseline.triangles
    assert compensated.stats.xy_compensation_mm == 0.0
    assert compensated.stats.z_compensation_mm == 0.0


def test_z_compensation_shifts_geometry_along_the_build_axis() -> None:
    # _QUAD lies in the z=0 plane with +z winding, so its vertex normals point +z.
    # A +z compensation must lift every surface point by that amount and is
    # recorded in the stats so a manifest can report what the mesh contains.
    base = build_aligner_shell(_QUAD, thickness_mm=0.6)
    shifted = build_aligner_shell(_QUAD, thickness_mm=0.6, z_compensation_mm=0.1)

    base_min_z = min(v[2] for tri in base.triangles for v in tri)
    shifted_min_z = min(v[2] for tri in shifted.triangles for v in tri)
    assert shifted_min_z == pytest.approx(base_min_z + 0.1, abs=1e-6)
    assert shifted.stats.z_compensation_mm == pytest.approx(0.1, abs=1e-9)


def test_compensation_preserves_wall_thickness() -> None:
    # Compensation biases inner and outer surfaces equally, so the measured
    # inner-to-outer wall thickness must stay at the requested sheet thickness.
    result = build_aligner_shell(
        _QUAD, thickness_mm=0.6, xy_compensation_mm=0.05, z_compensation_mm=0.05
    )
    assert result.stats.measured_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.min_thickness_mm == pytest.approx(0.6, abs=1e-6)
    assert result.stats.watertight is True


def test_gingival_trim_removes_geometry_below_the_plane() -> None:
    # Keep only y >= 5 (the "crown" half); the lower half is trimmed off.
    trim = TrimPlane(point=(0.0, 5.0, 0.0), normal=(0.0, 1.0, 0.0))
    result = build_aligner_shell(_strip(), thickness_mm=0.5, trim=trim)
    assert result.stats.trimmed is True
    assert result.stats.watertight is True
    lowest_y = min(v[1] for tri in result.triangles for v in tri)
    assert lowest_y >= 5.0


def test_trim_that_removes_everything_is_rejected() -> None:
    trim = TrimPlane(point=(0.0, 100.0, 0.0), normal=(0.0, 1.0, 0.0))
    with pytest.raises(ValueError, match="entire surface"):
        build_aligner_shell(_strip(), thickness_mm=0.5, trim=trim)
