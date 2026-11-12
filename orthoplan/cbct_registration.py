"""Explicit registration imports for CBCT mask proposal generation."""

from typing import Any
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.assets import CaseRecord
from orthoplan.model.registration import (
    RegistrationMethod,
    RegistrationQuality,
    RegistrationTransform,
)
from orthoplan.volume_proposals import VolumeProposalUnavailable
from orthoplan.planning.registered_anatomy import rigid_matrix


def _registration_for_payload(
    plan: TreatmentPlan, cbct_record: CaseRecord, payload: dict[str, Any]
) -> RegistrationTransform:
    if payload.get("registration_review") is not None:
        return _reviewed_transform(plan, cbct_record, payload)
    registration_id = str(payload.get("registration_id") or "")
    if registration_id:
        for reg in plan.registrations:
            if reg.id == registration_id:
                if (
                    not reg.is_acceptable
                    or reg.target_cbct_record_id != cbct_record.id
                    or not rigid_matrix(reg.matrix)
                ):
                    raise VolumeProposalUnavailable(
                        "selected registration is not accepted with quality metrics"
                    )
                return reg
        raise ValueError(f"unknown registration {registration_id!r}")

    if payload.get("mask", {}).get("voxel_to_patient_mm") is not None:
        raise ValueError("Patient-space masks require an explicit reviewed registration transform")
    source_asset_id = str(payload.get("source_stl_asset_id") or "")
    if not source_asset_id and plan.scans:
        source_asset_id = plan.scans[0].asset.id
    if source_asset_id not in plan.asset_ids:
        raise ValueError("source_stl_asset_id must reference a scan or mesh asset in the plan")

    accepted = payload.get("registration_accepted") is True
    quality_payload = payload.get("registration_quality")
    quality = _quality(quality_payload)
    if not accepted or quality is None:
        raise VolumeProposalUnavailable(
            "mask import requires an explicitly accepted registration with quality metrics"
        )
    return RegistrationTransform(
        id=str(
            payload.get("new_registration_id") or f"imported-{cbct_record.id}-{source_asset_id}"
        ),
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
        if isinstance(raw.get("notes"), list)
        else [],
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _reviewed_transform(plan, cbct_record, payload):
    packet = payload["registration_review"]
    if not isinstance(packet, dict) or payload.get("registration_accepted") is not True:
        raise ValueError("Inspect and explicitly accept the registration before importing masks")
    registration = RegistrationTransform.model_validate(packet.get("registration"))
    if (
        registration.target_cbct_record_id != cbct_record.id
        or registration.source_stl_asset_id != payload.get("source_stl_asset_id")
    ):
        raise ValueError("Registration belongs to different scan or CBCT records")
    assets = {a.id: a for a in plan.mesh_assets}
    assets.update({s.asset.id: s.asset for s in plan.scans})
    asset = assets.get(registration.source_stl_asset_id)
    if (
        asset is None
        or asset.units.value != "mm"
        or not asset.sha256
        or packet.get("source_scan_sha256") != asset.sha256
    ):
        raise ValueError("Registration must match the millimeter scan and its source hash")
    digest = payload.get("mask", {}).get("source_digest")
    if not digest or packet.get("volume_source_digest") != digest:
        raise ValueError("Registration and masks come from different volume sources")
    if not rigid_matrix(registration.matrix) or registration.quality is None:
        raise ValueError(
            "Registration requires a finite proper rigid transform and measured quality"
        )
    return registration.model_copy(update={"accepted": True})
