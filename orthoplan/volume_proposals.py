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
from orthoplan.model.registration_gate import gate_registration
from orthoplan.volume_geometry import (
    VoxelIndex,
    boundary_voxel_count,
    connected_components,
    format_voxel,
    touches_boundary,
    voxel_bounds,
)


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
    volume_dimensions: tuple[int, int, int] | None = None
    min_root_component_voxels: int = 3
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
    gate = gate_registration(payload.registration)
    if not gate.open:
        raise VolumeProposalUnavailable(
            "registration quality gate is FAIL ("
            + "; ".join(gate.reasons)
            + ") - acceptance cannot override the recorded metrics"
        )


def _root_axis_proposals(payload: VolumeProposalInput) -> tuple[list[RootGeometry], list[ToothAxis]]:
    roots: list[RootGeometry] = []
    axes: list[ToothAxis] = []
    for tooth, voxels in sorted(payload.root_voxels_by_tooth.items()):
        kept, metrics = _clean_root_voxels(voxels, payload)
        if not kept:
            continue
        points = [_voxel_to_mm(v, payload.voxel_spacing_mm) for v in kept]
        centerline = _smooth_centerline(_centerline(points))
        metrics.update(_centerline_metrics(centerline))
        confidence = _quality_confidence(metrics, minimum=4, target=24)
        out_of_field = bool(metrics["touches_volume_boundary"])
        notes = _quality_notes("root", metrics)
        roots.append(
            RootGeometry(
                tooth=ToothId(value=tooth),
                source_cbct_record_id=payload.cbct_record.id,
                registration_id=payload.registration.id,
                model_provenance=payload.model_provenance,
                confidence=confidence,
                review_status=ReviewStatus.PROPOSED,
                out_of_field=out_of_field,
                centerline=centerline,
                notes=notes,
                quality_metrics=metrics,
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
                    out_of_field=out_of_field,
                    origin_mm=centerline[0],
                    direction=direction,
                    derived_from="raw-volume-root-proposal",
                    notes=_quality_notes("axis", metrics),
                    quality_metrics=metrics,
                )
            )
    return roots, axes


def _bone_proposals(payload: VolumeProposalInput) -> list[AlveolarBoneRecord]:
    bone: list[AlveolarBoneRecord] = []
    if payload.bone_voxels:
        metrics = _bone_metrics(payload.bone_voxels, payload)
        bone.append(
            AlveolarBoneRecord(
                source_cbct_record_id=payload.cbct_record.id,
                registration_id=payload.registration.id,
                model_provenance=payload.model_provenance,
                confidence=_quality_confidence(metrics, minimum=8, target=96),
                review_status=ReviewStatus.PROPOSED,
                out_of_field=bool(metrics["touches_volume_boundary"]),
                boundary_volume_reference=f"{payload.cbct_record.id}:local-bone-mask",
                notes=_quality_notes("bone", metrics),
                quality_metrics=metrics,
            )
        )
    return bone


def _clean_root_voxels(
    voxels: list[VoxelIndex], payload: VolumeProposalInput
) -> tuple[list[VoxelIndex], dict[str, bool | float | int | str]]:
    components = connected_components(voxels)
    kept = [
        voxel
        for component in components
        if len(component) >= payload.min_root_component_voxels
        for voxel in component
    ]
    source = kept or list(dict.fromkeys(voxels))
    kept_components = [c for c in components if len(c) >= payload.min_root_component_voxels]
    largest = max((len(c) for c in components), default=0)
    metrics = _mask_metrics(source, payload)
    metrics.update({
        "input_voxel_count": len(set(voxels)),
        "component_count": len(components),
        "kept_component_count": len(kept_components) or int(bool(source)),
        "dropped_component_count": max(0, len(components) - len(kept_components)),
        "largest_component_fraction": round(largest / len(set(voxels)), 3) if voxels else 0.0,
    })
    return source, metrics


def _bone_metrics(
    voxels: list[VoxelIndex], payload: VolumeProposalInput
) -> dict[str, bool | float | int | str]:
    metrics = _mask_metrics(voxels, payload)
    metrics["boundary_voxel_count"] = boundary_voxel_count(set(voxels))
    return metrics


def _mask_metrics(
    voxels: list[VoxelIndex], payload: VolumeProposalInput
) -> dict[str, bool | float | int | str]:
    unique = set(voxels)
    bounds = voxel_bounds(unique)
    return {
        "voxel_count": len(unique),
        "bbox_min": format_voxel(bounds[0]),
        "bbox_max": format_voxel(bounds[1]),
        "touches_volume_boundary": touches_boundary(unique, payload.volume_dimensions),
        "voxel_spacing_mm": ",".join(str(v) for v in payload.voxel_spacing_mm),
    }


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


def _smooth_centerline(centerline: list[Vec3]) -> list[Vec3]:
    if len(centerline) < 3:
        return centerline
    smoothed = [centerline[0]]
    for index in range(1, len(centerline) - 1):
        smoothed.append(_mean3(centerline[index - 1:index + 2]))
    smoothed.append(centerline[-1])
    return smoothed


def _centerline_metrics(centerline: list[Vec3]) -> dict[str, float | int]:
    length = 0.0
    for start, end in zip(centerline, centerline[1:]):
        length += sum((end[i] - start[i]) ** 2 for i in range(3)) ** 0.5
    return {
        "centerline_points": len(centerline),
        "centerline_length_mm": round(length, 3),
    }


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


def _quality_confidence(
    metrics: dict[str, bool | float | int | str], *, minimum: int, target: int
) -> float:
    count = int(metrics.get("voxel_count", 0))
    if count < minimum:
        return 0.1
    value = min(0.85, 0.25 + 0.6 * (count / target))
    if metrics.get("touches_volume_boundary"):
        value *= 0.65
    if float(metrics.get("largest_component_fraction", 1.0)) < 0.75:
        value *= 0.8
    return round(value, 3)


def _quality_notes(kind: str, metrics: dict[str, bool | float | int | str]) -> list[str]:
    notes = [f"raw-volume {kind} proposal; human review required before trust"]
    if metrics.get("touches_volume_boundary"):
        notes.append("mask touches the CBCT field boundary; proposal may be truncated")
    dropped = int(metrics.get("dropped_component_count", 0))
    if dropped:
        notes.append(f"dropped {dropped} small disconnected component(s) as likely noise")
    return notes
