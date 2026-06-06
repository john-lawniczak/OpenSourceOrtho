"""Generate the North Star example: a landmark-derived straightening plan for the
first tracked specimen (the bundled OrthoCAD upper/lower shells).

This is the canonical end-to-end "Generate Plan" demonstration. Instead of
arbitrary authored movements, it places per-tooth crown LANDMARKS on a realistic
arch and lets the deterministic pipeline derive everything from them: real
per-tooth deviation targets (arch-form fit), an IPR space budget, attachments on
moved teeth, and approximate per-tooth collision bounds.

HONESTY NOTE: the specimen files are fused whole-arch shells with no per-tooth
segmentation, so the landmark coordinates here are APPROXIMATE scaffolding
(``approximate=True``), not precise measurements of this patient's crowns.
Refining them to precise landmarks (or providing segmented meshes) is what raises
the plan above this baseline. Nothing here diagnoses, infers roots/bone, or
claims a plan is safe.

Re-run with:

    python examples/generate_north_star.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orthoplan.generation import generate_plan_payload
from orthoplan.io.serialization import write_plan
from orthoplan.model import (
    MeshAsset,
    MeshProvenance,
    MeshUnits,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)
from orthoplan.model.landmarks import ArchLandmarks, CrownLandmark
from orthoplan.model.settings import TimelineSettings
from orthoplan.planning.arch_analysis import crown_width

EXAMPLES_DIR = Path(__file__).resolve().parent
SPECIMEN_ID = "spec-07b7031938c84b1a9c98517b8bc4cdd3"
FIXED_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)

# Realistic arch curvature and dentition order (right molar -> left molar).
_CURV = 0.03  # y = -CURV * x^2 ; ~22 mm depth at x = 27 mm
_SPACING = 0.90  # center-to-center tighter than crown width -> mild crowding
_UPPER = ["17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27"]
_LOWER = ["47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37"]
# A few teeth sit off the smooth arch (the mild crowding this plan corrects).
_DEVIATIONS = {"12": (0.0, 2.2), "22": (0.0, -1.4), "13": (0.6, 0.0), "32": (0.0, 1.6), "41": (-0.5, 0.0)}


def _step_side(values: list[str], sign: int) -> dict[str, tuple[float, float]]:
    """Place teeth from the midline outward so the along-curve spacing between
    centers equals ~crown_width * _SPACING (Euclidean, not just x)."""
    pts: dict[str, tuple[float, float]] = {}
    x = sign * crown_width(values[0]) * _SPACING / 2  # first tooth half a width off midline
    for j, value in enumerate(values):
        if j > 0:
            d = crown_width(value) * _SPACING
            slope = 2 * _CURV * abs(x)
            x += sign * d / (1 + slope * slope) ** 0.5  # advance along the curve
        pts[value] = (round(x, 3), round(-_CURV * x * x, 3))
    return pts


def _arch_landmarks(order: list[str]) -> list[CrownLandmark]:
    half = len(order) // 2
    right = _step_side(order[:half][::-1], -1)  # midline outward to the right molar
    left = _step_side(order[half:], +1)
    out: list[CrownLandmark] = []
    for value, (x, y) in {**right, **left}.items():
        dx, dy = _DEVIATIONS.get(value, (0.0, 0.0))
        out.append(CrownLandmark(tooth={"system": "FDI", "value": value}, x_mm=round(x + dx, 3),
                                 y_mm=round(y + dy, 3), approximate=True,
                                 source="scaffold-approximate (pending precise placement)"))
    return out


def _scan(asset_id: str, filename: str, arch: str) -> UploadedScan:
    asset = MeshAsset(id=asset_id, format="stl-binary", provenance=MeshProvenance.PATIENT_DERIVED,
                      units=MeshUnits.MM, vertex_count=0, face_count=0, created_at=FIXED_TS,
                      reference=filename)
    return UploadedScan(asset=asset, arch=arch, source="intraoral-scan")


def _landmarks() -> ArchLandmarks:
    return ArchLandmarks(landmarks=_arch_landmarks(_UPPER) + _arch_landmarks(_LOWER))


def _seed_plan() -> TreatmentPlan:
    return TreatmentPlan(
        id="north-star-canonical-001",
        title=f"North Star - landmark-derived alignment for specimen {SPECIMEN_ID}",
        settings=TreatmentSettings(timeline=TimelineSettings(wear_interval_days=14)),
        scans=[_scan("north-star-upper", "308806025_shell_occlusion_u.stl", "maxillary"),
               _scan("north-star-lower", "308806025_shell_occlusion_l.stl", "mandibular")],
    )


def main() -> None:
    result = generate_plan_payload(
        {"plan": _seed_plan().model_dump(mode="json"), "landmarks": _landmarks().model_dump(mode="json")}
    )
    if not result.get("ok"):
        raise SystemExit(f"generation failed: {result.get('errors')}")

    generated = TreatmentPlan.model_validate(result["plan"])
    write_plan(generated, EXAMPLES_DIR / "north_star_canonical_plan.json")

    timeline = result["timeline"]
    months = round(timeline["projected_duration_days"] / 30.0, 1)
    space = result["space"]
    print("Wrote north_star_canonical_plan.json")
    print(f"  source:      {result['source']}")
    print(f"  correctness: {result['correctness']['verdict']}")
    print(f"  stages:      {result['stage_count']}  (~{months} months at "
          f"{timeline['wear_interval_days']}-day wear)")
    print(f"  space:       {space['discrepancy_mm']} mm crowding, {space['ipr_count']} IPR, "
          f"{space['attachment_count']} attachments, residual {space['residual_mm']} mm")
    print(f"  findings:    {len(result['deterministic_findings'])} deterministic")


if __name__ == "__main__":
    main()
