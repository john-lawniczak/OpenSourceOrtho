"""Synthetic CBCT volume proposal benchmarks and fail-closed checks."""

from __future__ import annotations

from orthoplan.model.assets import CaseRecord
from orthoplan.model.registration import RegistrationQuality, RegistrationTransform
from orthoplan.validation.benchmark_models import BenchmarkMetric
from orthoplan.volume_proposals import (
    VolumeProposalInput,
    VolumeProposalUnavailable,
    propose_cbct_anatomy_from_volume,
)


def volume_proposal_metrics() -> list[BenchmarkMetric]:
    """Run non-PHI synthetic volume checks for Phase 12a/12c."""

    cbct, accepted = _fixture_record_and_registration()
    proposal = propose_cbct_anatomy_from_volume(_fixture_payload(cbct, accepted))
    trusted_count = sum(1 for obj in proposal.all_objects() if obj.trusted)
    return [
        _metric(
            "raw_volume_proposal_roots",
            float(len(proposal.roots)),
            "cbct-volume",
            "synthetic-open-volume",
            notes="Synthetic non-PHI sparse mask root proposals.",
        ),
        _metric(
            "raw_volume_proposal_axes",
            float(len(proposal.tooth_axes)),
            "cbct-volume",
            "synthetic-open-volume",
        ),
        _metric(
            "raw_volume_proposal_bone_records",
            float(len(proposal.alveolar_bone)),
            "cbct-volume",
            "synthetic-open-volume",
        ),
        _metric(
            "raw_volume_proposal_trusted_objects",
            float(trusted_count),
            "cbct-volume",
            "synthetic-open-volume",
            notes="Must remain 0 until human review accepts/corrects proposals.",
        ),
        _metric(
            "raw_volume_unaccepted_registration_fails_closed",
            _unaccepted_registration_fails_closed(cbct, accepted),
            "cbct-volume",
            "synthetic-open-volume",
        ),
        _metric(
            "raw_volume_noise_components_dropped",
            _dropped_components(proposal),
            "cbct-volume",
            "synthetic-open-volume",
        ),
        _metric(
            "raw_volume_boundary_truncation_flags",
            _boundary_flags(proposal),
            "cbct-volume",
            "synthetic-open-volume",
            notes="Counts proposal objects flagged out-of-field by volume boundary contact.",
        ),
    ]


def _fixture_record_and_registration() -> tuple[CaseRecord, RegistrationTransform]:
    cbct = CaseRecord(id="synthetic-open-volume", kind="cbct", local_reference="records/open.cbct")
    return cbct, RegistrationTransform(
        id="synthetic-reg",
        source_stl_asset_id="scan",
        target_cbct_record_id=cbct.id,
        quality=RegistrationQuality(method="synthetic", rmse_mm=0.0, fitness=1.0),
        accepted=True,
    )


def _fixture_payload(
    cbct: CaseRecord, registration: RegistrationTransform
) -> VolumeProposalInput:
    return VolumeProposalInput(
        cbct_record=cbct,
        registration=registration,
        root_voxels_by_tooth={
            "11": [(10, 10, z) for z in range(5)] + [(1, 1, 1)],
            "21": [(14, 10, z) for z in range(5)],
        },
        bone_voxels=[(x, y, z) for x in range(8) for y in range(2) for z in range(4)],
        voxel_spacing_mm=(0.3, 0.3, 0.5),
        volume_dimensions=(8, 16, 8),
        model_provenance="synthetic-volume-fixture",
    )


def _unaccepted_registration_fails_closed(
    cbct: CaseRecord, accepted: RegistrationTransform
) -> float:
    unaccepted = accepted.model_copy(update={"id": "synthetic-reg-proposed", "accepted": False})
    try:
        propose_cbct_anatomy_from_volume(
            VolumeProposalInput(
                cbct_record=cbct,
                registration=unaccepted,
                root_voxels_by_tooth={"11": [(0, 0, 0)]},
                bone_voxels=[],
            )
        )
    except VolumeProposalUnavailable:
        return 1.0
    return 0.0


def _dropped_components(proposal) -> float:
    return float(sum(int(root.quality_metrics.get("dropped_component_count", 0)) for root in proposal.roots))


def _boundary_flags(proposal) -> float:
    return float(sum(1 for obj in proposal.all_objects() if obj.out_of_field))


def _metric(
    name: str,
    value: float,
    component: str,
    case_id: str,
    *,
    notes: str | None = None,
) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        value=round(value, 6),
        component=component,
        case_id=case_id,
        notes=notes,
    )
