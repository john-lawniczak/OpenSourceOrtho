"""Deterministic acquisition advisor.

The advisor estimates what the engine could reassess if one missing data
modality became available. It only toggles availability flags or scan-unit
confirmation, reuses ``run_rules`` and ``data_gaps``, and never predicts what
new data would show.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from orthoplan.evaluation.engine import run_rules
from orthoplan.evaluation.finding import Finding
from orthoplan.model.assets import MeshUnits
from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan, UploadedScan

ACQUISITION_CAVEAT = (
    "This estimates what the deterministic engine could assess if data were available. "
    "It is not a treatment recommendation and predicts nothing about what the data would show."
)

SEVERITY_WEIGHT = {"warning": 3.0, "notice": 2.0, "info": 1.0}


class FindingRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: str
    category: str
    title: str


class GapImpact(BaseModel):
    model_config = ConfigDict(frozen=True)

    modality: str
    label: str
    acquisition: str
    resolves: list[FindingRef] = Field(default_factory=list)
    surfaces: list[FindingRef] = Field(default_factory=list)
    closes_data_gaps: list[str] = Field(default_factory=list)
    unlocks_assessment: bool = False
    priority_score: float = 0.0
    note: str


class AcquisitionAdvice(BaseModel):
    model_config = ConfigDict(frozen=True)

    baseline_finding_count: int
    baseline_data_gaps: list[str] = Field(default_factory=list)
    impacts: list[GapImpact] = Field(default_factory=list)
    caveat: str = ACQUISITION_CAVEAT


@dataclass(frozen=True)
class _Modality:
    key: str
    label: str
    acquisition: str
    applies: Callable[[TreatmentPlan], bool]
    toggle: Callable[[TreatmentPlan], TreatmentPlan]


def _with_data(plan: TreatmentPlan, **updates: bool) -> TreatmentPlan:
    data = plan.data.model_copy(update=updates)
    return plan.model_copy(update={"data": data})


def _confirm_scan_units(plan: TreatmentPlan) -> TreatmentPlan:
    scans: list[UploadedScan] = []
    for scan in plan.scans:
        asset = scan.asset.model_copy(update={"units": MeshUnits.MM})
        scans.append(scan.model_copy(update={"asset": asset}))
    return plan.model_copy(update={"scans": scans})


_MODALITIES = (
    _Modality(
        "roots",
        "Root data",
        "Acquire root-aware records or root geometry.",
        lambda p: not p.data.roots,
        lambda p: _with_data(p, roots=True),
    ),
    _Modality(
        "cbct",
        "CBCT (3D root/bone imaging)",
        "Acquire CBCT or equivalent 3D root/bone imaging when it is part of the chosen records.",
        lambda p: not p.data.cbct,
        lambda p: _with_data(p, cbct=True),
    ),
    _Modality(
        "periodontal_status",
        "Periodontal status",
        "Acquire or attach periodontal status records.",
        lambda p: not p.data.periodontal_status,
        lambda p: _with_data(p, periodontal_status=True),
    ),
    _Modality(
        "occlusion_scan",
        "Occlusion scan",
        "Acquire bite/occlusion records.",
        lambda p: not p.data.occlusion_scan,
        lambda p: _with_data(p, occlusion_scan=True),
    ),
    _Modality(
        "segmented_teeth",
        "Per-tooth segmentation",
        "Provide per-tooth segmentation or tooth mesh links.",
        lambda p: not p.data.segmented_teeth and not p.tooth_meshes,
        lambda p: _with_data(p, segmented_teeth=True),
    ),
    _Modality(
        "photos",
        "Photos",
        "Attach photos for human review context.",
        lambda p: not p.data.photos,
        lambda p: _with_data(p, photos=True),
    ),
    _Modality(
        "radiographs",
        "Radiographs",
        "Attach radiographs for human review context.",
        lambda p: not p.data.radiographs,
        lambda p: _with_data(p, radiographs=True),
    ),
    _Modality(
        "clinician_notes",
        "Treatment notes",
        "Attach treatment notes, goals, or the explicit review question.",
        lambda p: not p.data.clinician_notes,
        lambda p: _with_data(p, clinician_notes=True),
    ),
    _Modality(
        "scan_units_confirmed",
        "Confirm scan units",
        "Confirm scan units and scale for every uploaded scan.",
        lambda p: bool(p.scans) and not p.scale_confirmed,
        _confirm_scan_units,
    ),
)


def finding_key(finding: Finding) -> tuple[str, str, str, str]:
    return (
        finding.severity.value,
        finding.category.value,
        finding.title,
        finding.message,
    )


def _ref(finding: Finding) -> FindingRef:
    return FindingRef(
        severity=finding.severity.value,
        category=finding.category.value,
        title=finding.title,
    )


def _score(findings: list[FindingRef], gaps: list[str]) -> float:
    return sum(SEVERITY_WEIGHT.get(f.severity, 0.0) for f in findings) + len(gaps) * 0.5


def applicable_modalities(plan: TreatmentPlan) -> list[str]:
    return [modality.key for modality in _MODALITIES if modality.applies(plan)]


def acquisition_advice(plan: TreatmentPlan) -> AcquisitionAdvice:
    baseline_findings = run_rules(plan)
    baseline_by_key = {finding_key(finding): finding for finding in baseline_findings}
    baseline_gaps = data_gaps(plan)
    impacts: list[GapImpact] = []

    for modality in _MODALITIES:
        if not modality.applies(plan):
            continue
        counterfactual = modality.toggle(plan)
        cf_findings = run_rules(counterfactual)
        cf_by_key = {finding_key(finding): finding for finding in cf_findings}
        resolved = [
            _ref(baseline_by_key[key])
            for key in sorted(baseline_by_key.keys() - cf_by_key.keys())
        ]
        surfaced = [
            _ref(cf_by_key[key])
            for key in sorted(cf_by_key.keys() - baseline_by_key.keys())
        ]
        closed = [gap for gap in baseline_gaps if gap not in data_gaps(counterfactual)]
        score = _score(resolved + surfaced, closed)
        impacts.append(
            GapImpact(
                modality=modality.key,
                label=modality.label,
                acquisition=modality.acquisition,
                resolves=resolved,
                surfaces=surfaced,
                closes_data_gaps=closed,
                unlocks_assessment=bool(surfaced),
                priority_score=score,
                note=_note(resolved, surfaced, closed),
            )
        )

    impacts.sort(key=lambda impact: (-impact.priority_score, impact.modality))
    return AcquisitionAdvice(
        baseline_finding_count=len(baseline_findings),
        baseline_data_gaps=baseline_gaps,
        impacts=impacts,
    )


def _note(resolved: list[FindingRef], surfaced: list[FindingRef], closed: list[str]) -> str:
    parts: list[str] = []
    if resolved:
        parts.append("The engine would no longer flag findings caused only by this missing data.")
    if surfaced:
        parts.append(
            "The engine would run checks that are currently suppressed and may surface findings."
        )
    if closed:
        parts.append("The named data-gap entries would close.")
    if not parts:
        return "No current deterministic finding depends on this modality."
    return " ".join(parts)
