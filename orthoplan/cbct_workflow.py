"""CBCT-to-reviewed-anatomy workflow payloads.

The browser/server workflow intentionally treats raw-volume anatomy as imported
review material, not as trusted clinical segmentation. A local volume tool may
produce sparse masks; this module converts those masks into provenance-bound
``PROPOSED`` anatomy records and applies explicit review decisions.
"""

from __future__ import annotations

from typing import Any

from orthoplan.model.anatomy import DerivedAnatomy, ReviewStatus
from orthoplan.model.assets import CaseRecord
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.registration import (
    RegistrationMethod,
    RegistrationQuality,
    RegistrationTransform,
)
from orthoplan.volume_proposals import (
    VolumeProposalInput,
    VolumeProposalUnavailable,
    propose_cbct_anatomy_from_volume,
)

VoxelJson = list[int | float]


def cbct_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return inspectable CBCT records and registration/anatomy readiness."""

    plan = _plan(payload)
    records = [r for r in plan.case_records if r.kind in {"cbct", "dicom"}]
    return {
        "ok": True,
        "cbct_records": [_record_summary(r) for r in records],
        "registrations": [r.model_dump(mode="json") for r in plan.registrations],
        "derived_anatomy": _anatomy_json(plan.derived_anatomy),
        "ready": {
            "has_cbct": bool(records),
            "has_accepted_registration": any(r.is_acceptable for r in plan.registrations),
            "has_trusted_anatomy": bool(plan.derived_anatomy and plan.derived_anatomy.has_trusted),
        },
    }


def cbct_proposal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build untrusted anatomy proposals from imported sparse CBCT masks."""

    try:
        plan = _plan(payload)
        cbct_record = _find_cbct_record(plan, str(payload.get("cbct_record_id") or ""))
        registration = _registration_for_payload(plan, cbct_record, payload)
        mask = payload.get("mask") if isinstance(payload.get("mask"), dict) else payload
        proposal = propose_cbct_anatomy_from_volume(
            VolumeProposalInput(
                cbct_record=cbct_record,
                registration=registration,
                root_voxels_by_tooth=_root_voxels(mask.get("root_voxels_by_tooth", {})),
                bone_voxels=_voxels(mask.get("bone_voxels", []), field="bone_voxels"),
                voxel_spacing_mm=_float3(mask.get("voxel_spacing_mm"), default=(1.0, 1.0, 1.0)),
                volume_dimensions=_int3_or_none(mask.get("volume_dimensions")),
                min_root_component_voxels=int(mask.get("min_root_component_voxels", 3)),
                model_provenance=str(mask.get("model_provenance") or "local-volume-mask-import"),
            )
        )
    except (ValueError, VolumeProposalUnavailable) as exc:
        return {"ok": False, "errors": [str(exc)]}

    updated = plan.model_copy(
        update={
            "registrations": _upsert_registration(plan.registrations, registration),
            "derived_anatomy": _merge_anatomy(plan.derived_anatomy, proposal),
        }
    )
    return {
        "ok": True,
        "registration": registration.model_dump(mode="json"),
        "proposal": _anatomy_json(proposal),
        "plan": updated.model_dump(mode="json"),
        "caveat": (
            "Imported CBCT mask anatomy is proposed only. It is not trusted until "
            "a reviewer explicitly accepts or corrects each object."
        ),
    }


def cbct_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply explicit accept/correct/reject decisions to derived anatomy."""

    try:
        plan = _plan(payload)
        anatomy = plan.derived_anatomy
        if anatomy is None:
            raise ValueError("plan has no derived anatomy to review")
        decisions = payload.get("decisions")
        if not isinstance(decisions, list) or not decisions:
            raise ValueError("review decisions are required")
        updated = anatomy.model_copy(deep=True)
        for decision in decisions:
            _apply_decision(updated, decision)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}

    reviewed_plan = plan.model_copy(update={"derived_anatomy": updated})
    return {
        "ok": True,
        "derived_anatomy": _anatomy_json(updated),
        "plan": reviewed_plan.model_dump(mode="json"),
        "trusted_count": sum(1 for obj in updated.all_objects() if obj.trusted),
    }


def _plan(payload: dict[str, Any]) -> TreatmentPlan:
    raw = payload.get("plan")
    if not isinstance(raw, dict):
        raise ValueError("plan payload is required")
    return TreatmentPlan.model_validate(raw)


def _record_summary(record: CaseRecord) -> dict[str, Any]:
    dicom = record.dicom.model_dump(mode="json") if record.dicom else None
    return {
        "id": record.id,
        "kind": record.kind,
        "modality": record.modality,
        "filename": record.filename,
        "size_bytes": record.size_bytes,
        "local_reference": record.local_reference,
        "dicom": dicom,
    }


def _find_cbct_record(plan: TreatmentPlan, record_id: str) -> CaseRecord:
    records = [r for r in plan.case_records if r.kind in {"cbct", "dicom"}]
    if not records:
        raise ValueError("attach a CBCT/DICOM record before importing volume masks")
    if not record_id:
        return records[0]
    for record in records:
        if record.id == record_id:
            return record
    raise ValueError(f"unknown CBCT/DICOM record {record_id!r}")


def _registration_for_payload(
    plan: TreatmentPlan, cbct_record: CaseRecord, payload: dict[str, Any]
) -> RegistrationTransform:
    registration_id = str(payload.get("registration_id") or "")
    if registration_id:
        for reg in plan.registrations:
            if reg.id == registration_id:
                if not reg.is_acceptable:
                    raise VolumeProposalUnavailable(
                        "selected registration is not accepted with quality metrics"
                    )
                return reg
        raise ValueError(f"unknown registration {registration_id!r}")

    source_asset_id = str(payload.get("source_stl_asset_id") or "")
    if not source_asset_id and plan.scans:
        source_asset_id = plan.scans[0].asset.id
    if source_asset_id not in plan.asset_ids:
        raise ValueError("source_stl_asset_id must reference a scan or mesh asset in the plan")

    accepted = bool(payload.get("registration_accepted"))
    quality_payload = payload.get("registration_quality")
    quality = _quality(quality_payload)
    if not accepted or quality is None:
        raise VolumeProposalUnavailable(
            "mask import requires an explicitly accepted registration with quality metrics"
        )
    return RegistrationTransform(
        id=str(payload.get("new_registration_id") or f"imported-{cbct_record.id}-{source_asset_id}"),
        source_stl_asset_id=source_asset_id,
        target_cbct_record_id=cbct_record.id,
        method=RegistrationMethod.IMPORTED,
        quality=quality,
        accepted=True,
        operator=str(payload.get("operator") or "local reviewer"),
        model_provenance=str(payload.get("registration_provenance") or "imported-registration"),
        notes="Imported CBCT-to-STL registration accepted by reviewer for proposal generation.",
    )


def _quality(raw: Any) -> RegistrationQuality | None:
    if not isinstance(raw, dict):
        return None
    return RegistrationQuality(
        method=str(raw.get("method") or "imported"),
        rmse_mm=_optional_float(raw.get("rmse_mm")),
        inlier_ratio=_optional_float(raw.get("inlier_ratio")),
        fitness=_optional_float(raw.get("fitness")),
        notes=[str(n) for n in raw.get("notes", []) if str(n).strip()]
        if isinstance(raw.get("notes"), list) else [],
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _root_voxels(raw: Any) -> dict[str, list[tuple[int, int, int]]]:
    if not isinstance(raw, dict):
        raise ValueError("root_voxels_by_tooth must be an object")
    return {str(tooth): _voxels(voxels, field=f"root_voxels_by_tooth.{tooth}") for tooth, voxels in raw.items()}


def _voxels(raw: Any, *, field: str) -> list[tuple[int, int, int]]:
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be a list of [x,y,z] voxels")
    voxels: list[tuple[int, int, int]] = []
    for item in raw:
        if not isinstance(item, list | tuple) or len(item) != 3:
            raise ValueError(f"{field} contains an invalid voxel")
        voxels.append((int(item[0]), int(item[1]), int(item[2])))
    return voxels


def _float3(raw: Any, *, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if raw is None:
        return default
    if not isinstance(raw, list | tuple) or len(raw) != 3:
        raise ValueError("voxel_spacing_mm must be [x,y,z]")
    return (float(raw[0]), float(raw[1]), float(raw[2]))


def _int3_or_none(raw: Any) -> tuple[int, int, int] | None:
    if raw is None:
        return None
    if not isinstance(raw, list | tuple) or len(raw) != 3:
        raise ValueError("volume_dimensions must be [x,y,z]")
    return (int(raw[0]), int(raw[1]), int(raw[2]))


def _upsert_registration(
    registrations: list[RegistrationTransform], registration: RegistrationTransform
) -> list[RegistrationTransform]:
    out = [reg for reg in registrations if reg.id != registration.id]
    out.append(registration)
    return out


def _merge_anatomy(existing: DerivedAnatomy | None, proposal: DerivedAnatomy) -> DerivedAnatomy:
    if existing is None:
        return proposal
    return DerivedAnatomy(
        roots=[*existing.roots, *proposal.roots],
        tooth_axes=[*existing.tooth_axes, *proposal.tooth_axes],
        alveolar_bone=[*existing.alveolar_bone, *proposal.alveolar_bone],
    )


def _anatomy_json(anatomy: DerivedAnatomy | None) -> dict[str, Any] | None:
    if anatomy is None:
        return None

    def row(obj: Any) -> dict[str, Any]:
        data = obj.model_dump(mode="json")
        data["trusted"] = obj.trusted
        data["reviewed"] = obj.reviewed
        return data

    return {
        "has_trusted": anatomy.has_trusted,
        "roots": [row(r) for r in anatomy.roots],
        "tooth_axes": [row(a) for a in anatomy.tooth_axes],
        "alveolar_bone": [row(b) for b in anatomy.alveolar_bone],
    }


def _apply_decision(anatomy: DerivedAnatomy, decision: Any) -> None:
    if not isinstance(decision, dict):
        raise ValueError("each review decision must be an object")
    group = str(decision.get("group") or "")
    if group not in {"roots", "tooth_axes", "alveolar_bone"}:
        raise ValueError(f"unknown anatomy group {group!r}")
    index = int(decision.get("index", -1))
    items = getattr(anatomy, group)
    if index < 0 or index >= len(items):
        raise ValueError(f"anatomy index out of range for {group}")
    status = ReviewStatus(str(decision.get("review_status") or ""))
    notes = list(items[index].notes)
    note = str(decision.get("note") or "").strip()
    if note:
        notes.append(note)
    items[index] = items[index].model_copy(
        update={
            "review_status": status,
            "operator": str(decision.get("operator") or "local reviewer"),
            "notes": notes,
        }
    )
