"""Trusted CBCT axes -> non-approximate anatomical frames -> renderable rotation."""

from __future__ import annotations

import math

from orthoplan.model.anatomy import DerivedAnatomy, ReviewStatus, ToothAxis
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.geometry import ToothLocalFrame
from orthoplan.model.plan import SegmentedToothMesh, Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.planning.anatomical_frame import trusted_axis_frames, upgrade_tooth_mesh_frames
from orthoplan.viz.progress import build_stage_progress_frames


def _identity():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def _reg(*, rmse: float = 0.2) -> RegistrationTransform:
    return RegistrationTransform(
        id="reg1", source_stl_asset_id="scan", target_cbct_record_id="cb",
        accepted=True, matrix=_identity(),
        quality=RegistrationQuality(method="manual", rmse_mm=rmse),
    )


def _axis(tooth: str, *, status: ReviewStatus = ReviewStatus.ACCEPTED,
          direction=(0.0, 0.0, 1.0)) -> ToothAxis:
    return ToothAxis(
        tooth={"system": "FDI", "value": tooth},
        source_cbct_record_id="cb", registration_id="reg1",
        review_status=status, origin_mm=(0.0, 0.0, 0.0), direction=direction,
    )


def _pca_frame(x: float) -> ToothLocalFrame:
    return ToothLocalFrame(origin=(x, 0.0, 0.0), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def _plan(*, axes: list[ToothAxis], registration: RegistrationTransform | None = None,
          stages: list[Stage] | None = None) -> TreatmentPlan:
    teeth = ["11", "21"]
    assets = [
        MeshAsset(id=f"m{t}", format="stl-ascii", units=MeshUnits.MM, vertex_count=3, face_count=1)
        for t in teeth
    ]
    links = [
        SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="m11", local_frame=_pca_frame(-4.0)),
        SegmentedToothMesh(tooth=ToothId(value="21"), mesh_asset_id="m21", local_frame=_pca_frame(4.0)),
    ]
    return TreatmentPlan(
        id="p",
        scans=[UploadedScan(asset=MeshAsset(id="scan", format="stl", units=MeshUnits.MM,
                                            vertex_count=1, face_count=1))],
        case_records=[CaseRecord(id="cb", kind="cbct", local_reference="r/cb.dcm")],
        registrations=[registration or _reg()],
        mesh_assets=assets, tooth_meshes=links,
        derived_anatomy=DerivedAnatomy(tooth_axes=axes),
        stages=stages or [],
    )


def _is_unit(vector) -> bool:
    return math.isclose(sum(v * v for v in vector) ** 0.5, 1.0, abs_tol=1e-9)


def test_trusted_axis_builds_orthonormal_anatomical_frame() -> None:
    frames = trusted_axis_frames(_plan(axes=[_axis("11")]))
    frame = frames["11"]
    assert frame.approximate is False
    assert frame.source == "cbct-axis+arch-tangent"
    buccolingual, mesiodistal, long_axis = frame.axes
    assert all(_is_unit(axis) for axis in frame.axes)
    # Long axis is the trusted CBCT axis, oriented occlusally (+z).
    assert long_axis == (0.0, 0.0, 1.0)
    # Mesiodistal points along the arch toward the neighbour at x=+4.
    assert math.isclose(mesiodistal[0], 1.0, abs_tol=1e-9)
    # Orthonormal: pairwise dot products are zero.
    pairs = [(buccolingual, mesiodistal), (buccolingual, long_axis), (mesiodistal, long_axis)]
    assert all(abs(sum(a[i] * b[i] for i in range(3))) < 1e-9 for a, b in pairs)


def test_root_first_axis_direction_is_oriented_occlusally() -> None:
    frames = trusted_axis_frames(_plan(axes=[_axis("11", direction=(0.0, 0.0, -1.0))]))
    assert frames["11"].axes[2] == (0.0, 0.0, 1.0)


def test_proposed_axis_earns_no_frame() -> None:
    assert trusted_axis_frames(_plan(axes=[_axis("11", status=ReviewStatus.PROPOSED)])) == {}


def test_failed_registration_gate_earns_no_frame() -> None:
    plan = _plan(axes=[_axis("11")], registration=_reg(rmse=9.0))
    assert trusted_axis_frames(plan) == {}


def test_upgrade_replaces_only_approximate_frames() -> None:
    plan = upgrade_tooth_mesh_frames(_plan(axes=[_axis("11")]))
    by_tooth = {link.tooth.value: link.local_frame for link in plan.tooth_meshes}
    assert by_tooth["11"].approximate is False
    assert by_tooth["21"].approximate is True  # no trusted axis: PCA frame retained


def test_trusted_frame_makes_rotation_renderable_in_progress_frames() -> None:
    stage = Stage(index=0, deltas=[
        ToothDelta(tooth=ToothId(value="11"), rotate_rotation_deg=1.0),
        ToothDelta(tooth=ToothId(value="21"), rotate_rotation_deg=1.0),
    ])
    plan = upgrade_tooth_mesh_frames(_plan(axes=[_axis("11")], stages=[stage]))
    frames = build_stage_progress_frames(plan)
    renderable = {pose.tooth.value: pose.rotation_renderable for pose in frames[-1].poses}
    assert renderable == {"11": True, "21": False}
