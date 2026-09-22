from __future__ import annotations

import pytest

from orthoplan.model import (
    Arch,
    CaseRecord,
    MeshAsset,
    SegmentedToothMesh,
    Stage,
    ToothDelta,
    ToothId,
    TreatmentPlan,
)
from orthoplan.segmentation import link_tooth_mesh


def test_stage_rejects_duplicate_teeth() -> None:
    tooth = ToothId(value="11")

    with pytest.raises(ValueError, match="duplicate tooth"):
        Stage(index=0, deltas=[ToothDelta(tooth=tooth), ToothDelta(tooth=tooth)])


def test_plan_stage_indexes_must_be_contiguous() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        TreatmentPlan(id="example", stages=[Stage(index=1)])


def test_arch_is_derived_from_fdi_quadrant() -> None:
    assert ToothId(value="11").arch is Arch.MAXILLARY
    assert ToothId(value="31").arch is Arch.MANDIBULAR
    assert ToothDelta(tooth=ToothId(value="46")).arch is Arch.MANDIBULAR


def test_invalid_fdi_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        ToothId(value="99")  # quadrant 9 and position 9 are both invalid
    with pytest.raises(ValueError):
        ToothId(value="1")  # must be two digits


def test_mixed_coordinate_frame_is_rejected() -> None:
    with pytest.raises(ValueError, match="coordinate frame"):
        TreatmentPlan(
            id="frame",
            stages=[
                Stage(
                    index=0,
                    deltas=[ToothDelta(tooth=ToothId(value="11"), coordinate_frame="other")],
                )
            ],
        )


def test_segmented_tooth_mesh_link_can_be_referenced_by_delta() -> None:
    asset = MeshAsset(id="mesh-11", format="stl-binary", vertex_count=3, face_count=1)
    link = link_tooth_mesh(tooth=ToothId(value="11"), mesh_asset=asset)

    plan = TreatmentPlan(
        id="linked",
        mesh_assets=[asset],
        tooth_meshes=[link],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="mesh-11")],
            )
        ],
    )

    assert plan.segmented_tooth_values == {"11"}


def test_unknown_delta_mesh_link_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown segmented mesh"):
        TreatmentPlan(
            id="bad-link",
            stages=[
                Stage(
                    index=0,
                    deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="missing")],
                )
            ],
        )


def test_duplicate_segmented_tooth_mesh_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate segmented tooth"):
        TreatmentPlan(
            id="dupe-link",
            mesh_assets=[
                MeshAsset(id="mesh-a", format="stl-binary", vertex_count=3, face_count=1),
                MeshAsset(id="mesh-b", format="stl-binary", vertex_count=3, face_count=1),
            ],
            tooth_meshes=[
                SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-a"),
                SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="mesh-b"),
            ],
        )


def test_segmented_tooth_mesh_requires_known_asset() -> None:
    with pytest.raises(ValueError, match="unknown mesh asset"):
        TreatmentPlan(
            id="missing-asset",
            tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="11"), mesh_asset_id="missing")],
        )


def test_delta_cannot_reference_another_tooths_mesh() -> None:
    # mesh-21 is segmented to tooth 21; a delta for tooth 11 must not use it.
    asset = MeshAsset(id="mesh-21", format="stl-binary", vertex_count=3, face_count=1)
    with pytest.raises(ValueError, match="unknown segmented mesh"):
        TreatmentPlan(
            id="wrong-tooth",
            mesh_assets=[asset],
            tooth_meshes=[SegmentedToothMesh(tooth=ToothId(value="21"), mesh_asset_id="mesh-21")],
            stages=[
                Stage(
                    index=0,
                    deltas=[ToothDelta(tooth=ToothId(value="11"), mesh_asset_id="mesh-21")],
                )
            ],
        )


def test_duplicate_asset_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate mesh asset id"):
        TreatmentPlan(
            id="dupe-asset",
            mesh_assets=[
                MeshAsset(id="same", format="stl-binary", vertex_count=3, face_count=1),
                MeshAsset(id="same", format="stl-binary", vertex_count=3, face_count=1),
            ],
        )


def test_duplicate_case_record_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate case record id"):
        TreatmentPlan(
            id="dupe-record",
            case_records=[
                CaseRecord(id="same", kind="cbct"),
                CaseRecord(id="same", kind="photo"),
            ],
        )
