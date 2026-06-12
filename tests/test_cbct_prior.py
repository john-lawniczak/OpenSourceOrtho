"""CBCT boundary priors + cross-modal confidence (Step 2 of the CBCT path)."""

from __future__ import annotations

import math

from orthoplan.model.anatomy import DerivedAnatomy, ReviewStatus, RootGeometry, ToothAxis
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.geometry import apply_affine, invert_affine
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.segmentation.cbct_prior import boundary_priors_for_arch
from orthoplan.segmentation.heuristic import default_arch_order
from orthoplan.segmentation.hybrid import hybrid_segment_arch_with_diagnostics

Vec3 = tuple[float, float, float]


def _scan() -> UploadedScan:
    return UploadedScan(
        asset=MeshAsset(id="scan", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1)
    )


def _reg(*, rmse: float = 0.2, fitness: float | None = 0.9, matrix=None) -> RegistrationTransform:
    return RegistrationTransform(
        id="reg1", source_stl_asset_id="scan", target_cbct_record_id="cb",
        accepted=True, matrix=matrix or _identity(),
        quality=RegistrationQuality(method="manual", rmse_mm=rmse, fitness=fitness),
    )


def _identity():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def _root(tooth: str, x: float) -> RootGeometry:
    return RootGeometry(
        tooth={"system": "FDI", "value": tooth},
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=ReviewStatus.ACCEPTED,
        centerline=[(x, 0.0, 0.0), (x, 0.0, -8.0)],
    )


def _axis(tooth: str, x: float, *, status: ReviewStatus = ReviewStatus.ACCEPTED) -> ToothAxis:
    return ToothAxis(
        tooth={"system": "FDI", "value": tooth},
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=status, origin_mm=(x, 0.0, 0.0), direction=(0.0, 0.0, 1.0),
    )


def _plan(anatomy: DerivedAnatomy | None, registration: RegistrationTransform | None) -> TreatmentPlan:
    return TreatmentPlan(
        id="p", scans=[_scan()],
        case_records=[CaseRecord(id="cb", kind="cbct", local_reference="r/cb.dcm")],
        registrations=[registration] if registration else [],
        derived_anatomy=anatomy,
    )


def test_priors_are_adjacent_pair_midpoints_in_arch_order() -> None:
    anatomy = DerivedAnatomy(roots=[_root("11", -4.0), _root("21", 4.0), _root("22", 12.0)])
    priors = boundary_priors_for_arch(_plan(anatomy, _reg()), "maxillary")
    assert priors is not None
    assert priors.tooth_pairs == [("11", "21"), ("21", "22")]
    assert priors.points[0][0] == 0.0  # midpoint of -4 and 4
    assert priors.points[1][0] == 8.0
    assert priors.allow_confidence_boost is True


def test_priors_map_cbct_space_back_through_inverse_registration() -> None:
    # Registration maps scan -> CBCT as +10 mm in x, so CBCT anatomy at x must
    # come back at x - 10 in scan space.
    matrix = _identity()
    matrix[0][3] = 10.0
    anatomy = DerivedAnatomy(roots=[_root("11", 6.0), _root("21", 14.0)])
    priors = boundary_priors_for_arch(_plan(anatomy, _reg(matrix=matrix)), "maxillary")
    assert priors is not None
    assert math.isclose(priors.points[0][0], 0.0, abs_tol=1e-9)


def test_failed_gate_yields_no_priors() -> None:
    anatomy = DerivedAnatomy(roots=[_root("11", -4.0), _root("21", 4.0)])
    assert boundary_priors_for_arch(_plan(anatomy, _reg(rmse=9.0)), "maxillary") is None


def test_marginal_gate_biases_cuts_but_never_boosts_confidence() -> None:
    anatomy = DerivedAnatomy(roots=[_root("11", -4.0), _root("21", 4.0)])
    priors = boundary_priors_for_arch(_plan(anatomy, _reg(rmse=0.8)), "maxillary")
    assert priors is not None
    assert priors.allow_confidence_boost is False


def test_untrusted_anatomy_yields_no_priors() -> None:
    anatomy = DerivedAnatomy(
        tooth_axes=[_axis("11", -4.0, status=ReviewStatus.PROPOSED), _axis("21", 4.0, status=ReviewStatus.PROPOSED)]
    )
    assert boundary_priors_for_arch(_plan(anatomy, _reg()), "maxillary") is None


def test_single_trusted_tooth_is_not_enough() -> None:
    anatomy = DerivedAnatomy(roots=[_root("11", -4.0)])
    assert boundary_priors_for_arch(_plan(anatomy, _reg()), "maxillary") is None


def test_axis_origins_fill_in_for_missing_roots() -> None:
    anatomy = DerivedAnatomy(roots=[_root("11", -4.0)], tooth_axes=[_axis("21", 4.0)])
    priors = boundary_priors_for_arch(_plan(anatomy, _reg()), "maxillary")
    assert priors is not None
    assert priors.tooth_pairs == [("11", "21")]


def test_invert_affine_round_trips_points() -> None:
    matrix = [
        [0.0, -1.0, 0.0, 3.0],
        [1.0, 0.0, 0.0, -2.0],
        [0.0, 0.0, 1.0, 5.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    inverse = invert_affine(matrix)
    assert inverse is not None
    point = (1.5, -4.0, 2.0)
    mapped = apply_affine(matrix, point)
    back = apply_affine(inverse, mapped)
    assert all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(point, back))


def test_invert_affine_rejects_singular_matrix() -> None:
    singular = [[0.0] * 4 for _ in range(4)]
    singular[3][3] = 1.0
    assert invert_affine(singular) is None


# --- hybrid segmenter integration: prior-biased cuts + cross-modal confidence ---


def _arch_vertices(facets_per_tooth: int = 12) -> list[Vec3]:
    """Synthetic horseshoe arch (same shape as test_segmentation_auto)."""

    teeth = len(default_arch_order("maxillary"))
    total = teeth * facets_per_tooth
    vertices: list[Vec3] = []
    for i in range(total):
        theta = math.pi * (i / (total - 1))
        cx, cy = 20.0 * math.cos(theta), 20.0 * math.sin(theta)
        vertices.extend([(cx, cy, 0.0), (cx + 0.5, cy, 0.0), (cx, cy + 0.5, 0.3)])
    return vertices


def _tooth_arc_points(count: int = 14) -> list[Vec3]:
    """One synthetic 'tooth position' per canonical tooth along the same horseshoe."""

    out: list[Vec3] = []
    for index in range(count):
        theta = math.pi * ((index + 0.5) / count)
        out.append((20.0 * math.cos(theta), 20.0 * math.sin(theta), 0.0))
    return out


def test_hybrid_reports_cross_modal_agreement_for_matching_priors() -> None:
    teeth = _tooth_arc_points()
    prior_points = [
        ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0) for a, b in zip(teeth, teeth[1:])
    ]
    segments, diagnostics = hybrid_segment_arch_with_diagnostics(
        _arch_vertices(), arch="maxillary", prior_points=prior_points, prior_boost=True,
    )
    baseline, base_diag = hybrid_segment_arch_with_diagnostics(
        _arch_vertices(), arch="maxillary",
    )
    assert segments and diagnostics.cross_modal is not None
    assert base_diag.cross_modal is None
    assert diagnostics.cross_modal.boost_applied is True
    assert 0.0 <= diagnostics.cross_modal.mean_agreement <= 1.0
    # Same tooth labels as the surface-only pass; priors bias, never relabel.
    assert [s.tooth_value for s in segments] == [s.tooth_value for s in baseline]
    # Confidence stays bounded and valid under cross-modal calibration.
    assert all(0.0 <= s.confidence <= 0.93 for s in segments)


def test_hybrid_without_boost_never_raises_confidence_above_surface_only() -> None:
    teeth = _tooth_arc_points()
    prior_points = [
        ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0) for a, b in zip(teeth, teeth[1:])
    ]
    boosted, _diag = hybrid_segment_arch_with_diagnostics(
        _arch_vertices(), arch="maxillary", prior_points=prior_points, prior_boost=True,
    )
    capped, _diag2 = hybrid_segment_arch_with_diagnostics(
        _arch_vertices(), arch="maxillary", prior_points=prior_points, prior_boost=False,
    )
    surface, _diag3 = hybrid_segment_arch_with_diagnostics(_arch_vertices(), arch="maxillary")
    by_tooth = {s.tooth_value: s.confidence for s in surface}
    for segment in capped:
        assert segment.confidence <= by_tooth[segment.tooth_value] + 1e-9
    # With a PASS gate the calibrated confidence may exceed the surface-only score.
    assert any(s.confidence > by_tooth[s.tooth_value] for s in boosted)
