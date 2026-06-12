"""Optional CBCT volume proposal path for roots, axes, and alveolar bone.

This module is intentionally conservative. It turns redacted CBCT metadata and a
caller-supplied local threshold mask into derived-anatomy *proposals* only. It
does not store volume bytes, does not auto-trust anatomy, and does not require
the optional imaging stack at import time.
"""

from __future__ import annotations

from dataclasses import dataclass

from orthoplan.model.anatomy import (
    AlveolarBoneRecord,
    DerivedAnatomy,
    ReviewStatus,
    RootGeometry,
    ToothAxis,
)
from orthoplan.model.assets import CaseRecord
from orthoplan.model.geometry import Vec3
from orthoplan.model.identity import ToothId
from orthoplan.model.registration import RegistrationTransform

VoxelIndex = tuple[int, int, int]


class VolumeProposalUnavailable(RuntimeError):
    """Raised when the raw-volume proposal path cannot run."""


@dataclass(frozen=True)
class VolumeProposalInput:
    """Local, non-serialized input for optional CBCT proposal generation.

    ``root_voxels_by_tooth`` and ``bone_voxels`` are sparse threshold/label masks
    produced by an optional local imaging tool. They are consumed in memory and
    converted to redacted geometry summaries; plan JSON still carries no volume
    bytes.
    """

    cbct_record: CaseRecord
    registration: RegistrationTransform
    root_voxels_by_tooth: dict[str, list[VoxelIndex]]
    bone_voxels: list[VoxelIndex]
    voxel_spacing_mm: tuple[float, float, float] = (1.0, 1.0, 1.0)
    model_provenance: str = "local-volume-threshold-proposal"


def propose_cbct_anatomy_from_volume(payload: VolumeProposalInput) -> DerivedAnatomy:
    """Build untrusted derived-anatomy proposals from local CBCT volume masks."""

    _validate_payload(payload)
    roots, axes = _root_axis_proposals(payload)
    bone = _bone_proposals(payload)
    return DerivedAnatomy(roots=roots, tooth_axes=axes, alveolar_bone=bone)


def _validate_payload(payload: VolumeProposalInput) -> None:
    if payload.cbct_record.kind not in {"cbct", "dicom"}:
        raise ValueError("volume proposals require a CBCT/DICOM case record")
    if payload.registration.target_cbct_record_id != payload.cbct_record.id:
        raise ValueError("registration target must match the CBCT/DICOM record")
    if not payload.registration.is_acceptable:
        raise VolumeProposalUnavailable(
            "volume proposals require a human-accepted registration with quality metrics"
        )


def _root_axis_proposals(payload: VolumeProposalInput) -> tuple[list[RootGeometry], list[ToothAxis]]:
    roots: list[RootGeometry] = []
    axes: list[ToothAxis] = []
    for tooth, voxels in sorted(payload.root_voxels_by_tooth.items()):
        if not voxels:
            continue
        points = [_voxel_to_mm(v, payload.voxel_spacing_mm) for v in voxels]
        centerline = _centerline(points)
        confidence = _mask_confidence(len(points), minimum=4, target=24)
        notes = ["raw-volume root proposal; human review required before trust"]
        roots.append(
            RootGeometry(
                tooth=ToothId(value=tooth),
                source_cbct_record_id=payload.cbct_record.id,
                registration_id=payload.registration.id,
                model_provenance=payload.model_provenance,
                confidence=confidence,
                review_status=ReviewStatus.PROPOSED,
                centerline=centerline,
                notes=notes,
            )
        )
        if len(centerline) >= 2:
            direction = _unit(
                tuple(  # type: ignore[arg-type]
                    centerline[-1][i] - centerline[0][i] for i in range(3)
                )
            )
            axes.append(
                ToothAxis(
                    tooth=ToothId(value=tooth),
                    source_cbct_record_id=payload.cbct_record.id,
                    registration_id=payload.registration.id,
                    model_provenance=payload.model_provenance,
                    confidence=confidence,
                    review_status=ReviewStatus.PROPOSED,
                    origin_mm=centerline[0],
                    direction=direction,
                    derived_from="raw-volume-root-proposal",
                    notes=["raw-volume axis proposal; human review required before trust"],
                )
            )
    return roots, axes


def _bone_proposals(payload: VolumeProposalInput) -> list[AlveolarBoneRecord]:
    bone: list[AlveolarBoneRecord] = []
    if payload.bone_voxels:
        bone.append(
            AlveolarBoneRecord(
                source_cbct_record_id=payload.cbct_record.id,
                registration_id=payload.registration.id,
                model_provenance=payload.model_provenance,
                confidence=_mask_confidence(len(payload.bone_voxels), minimum=8, target=96),
                review_status=ReviewStatus.PROPOSED,
                boundary_volume_reference=f"{payload.cbct_record.id}:local-bone-mask",
                notes=["raw-volume alveolar bone proposal; human review required before trust"],
            )
        )
    return bone


def _voxel_to_mm(voxel: VoxelIndex, spacing: tuple[float, float, float]) -> Vec3:
    return (
        float(voxel[0]) * spacing[0],
        float(voxel[1]) * spacing[1],
        float(voxel[2]) * spacing[2],
    )


def _centerline(points: list[Vec3]) -> list[Vec3]:
    """Approximate a root centerline from sparse voxels by z-slice centroids."""

    by_z: dict[float, list[Vec3]] = {}
    for point in points:
        by_z.setdefault(point[2], []).append(point)
    return [_mean3(by_z[z]) for z in sorted(by_z)]


def _mean3(points: list[Vec3]) -> Vec3:
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
        sum(p[2] for p in points) / len(points),
    )


def _unit(vector: Vec3) -> Vec3:
    length = sum(v * v for v in vector) ** 0.5
    if length == 0:
        return (0.0, 0.0, 1.0)
    return tuple(v / length for v in vector)  # type: ignore[return-value]


def _mask_confidence(count: int, *, minimum: int, target: int) -> float:
    if count < minimum:
        return 0.1
    return round(min(0.85, 0.25 + 0.6 * (count / target)), 3)
