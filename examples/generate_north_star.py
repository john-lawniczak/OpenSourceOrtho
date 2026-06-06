"""Generate the North Star example: a generated straightening plan for the first
tracked specimen (the bundled OrthoCAD upper/lower shells).

This is the canonical end-to-end demonstration of "Generate Plan": it loads the
specimen scans, applies a clinically-plausible MILD anterior-alignment target,
and runs the real deterministic generator + orchestration pipeline to produce a
cap-respecting staged plan that projects to roughly 4-6 months.

IMPORTANT HONESTY NOTE: the two specimen files are fused whole-arch shells with
no per-tooth segmentation, and the engine never auto-segments or infers a target
from raw geometry. So the per-tooth movements below are AUTHORED estimates of a
mild correction, not measurements of this patient's crown positions. With
segmented per-tooth meshes the same button would instead derive the target from
the visible geometry. Nothing here is a diagnosis, treatment plan, or approval.

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
    Stage,
    TimelineSettings,
    ToothDelta,
    ToothId,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)
from orthoplan.model.plan import TreatmentPlan as _Plan  # noqa: F401 (clarity)

EXAMPLES_DIR = Path(__file__).resolve().parent
SPECIMEN_ID = "spec-07b7031938c84b1a9c98517b8bc4cdd3"
# Fixed timestamp so regenerating does not churn the checked-in JSON.
FIXED_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)

# Authored MILD anterior-alignment target (cumulative per-tooth totals). The
# driving correction is a ~20 deg derotation, which at the 2 deg/stage rotation
# cap and 14-day wear lands the projection in the 4-6 month range. Everything
# else is sub-millimeter - a "somewhat straight already" case.
TARGET_TOTALS: list[dict] = [
    {"value": "12", "translate_y_mm": 0.4, "rotate_rotation_deg": 10.0},
    {"value": "11", "translate_x_mm": 0.8},
    {"value": "21", "translate_x_mm": -0.6},
    {"value": "22", "translate_y_mm": 0.5, "rotate_rotation_deg": 20.0},
    {"value": "13", "translate_x_mm": 0.4},
    {"value": "23", "translate_x_mm": -0.4},
    {"value": "31", "translate_x_mm": 0.5},
    {"value": "41", "translate_x_mm": -0.5},
    {"value": "32", "translate_y_mm": 0.4, "rotate_rotation_deg": 12.0},
]


def _scan(asset_id: str, filename: str, arch: str) -> UploadedScan:
    asset = MeshAsset(
        id=asset_id,
        format="stl-binary",
        provenance=MeshProvenance.PATIENT_DERIVED,
        units=MeshUnits.MM,
        vertex_count=0,
        face_count=0,
        created_at=FIXED_TS,
        reference=filename,
    )
    return UploadedScan(asset=asset, arch=arch, source="intraoral-scan")


def _seed_plan() -> TreatmentPlan:
    """The pre-generation plan: specimen scans + authored mild target totals."""
    deltas = [ToothDelta(tooth=ToothId(value=t["value"]), **{k: v for k, v in t.items() if k != "value"})
              for t in TARGET_TOTALS]
    return TreatmentPlan(
        id="north-star-canonical-001",
        title=f"North Star - generated mild alignment for specimen {SPECIMEN_ID}",
        settings=TreatmentSettings(timeline=TimelineSettings(wear_interval_days=14)),
        scans=[
            _scan("north-star-upper", "308806025_shell_occlusion_u.stl", "maxillary"),
            _scan("north-star-lower", "308806025_shell_occlusion_l.stl", "mandibular"),
        ],
        stages=[Stage(index=0, deltas=deltas)],
    )


def main() -> None:
    result = generate_plan_payload({"plan": _seed_plan().model_dump(mode="json")})
    if not result.get("ok"):
        raise SystemExit(f"generation failed: {result.get('errors')}")

    generated = TreatmentPlan.model_validate(result["plan"])
    write_plan(generated, EXAMPLES_DIR / "north_star_canonical_plan.json")

    timeline = result["timeline"]
    months = round(timeline["projected_duration_days"] / 30.0, 1)
    print("Wrote north_star_canonical_plan.json")
    print(f"  source:      {result['source']}")
    print(f"  correctness: {result['correctness']['verdict']}")
    print(f"  stages:      {result['stage_count']}")
    print(f"  projection:  {timeline['projected_duration_days']} days (~{months} months) "
          f"at {timeline['wear_interval_days']}-day wear")
    print(f"  findings:    {len(result['deterministic_findings'])} deterministic")


if __name__ == "__main__":
    main()
