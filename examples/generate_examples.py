"""Generate the synthetic example plans checked into this directory.

Everything here is fabricated - no patient data. Re-run with:

    python examples/generate_examples.py

The checked-in JSON lets contributors immediately try, e.g.:

    orthoplan plan-summary examples/basic_plan.json
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orthoplan.io.serialization import write_plan
from orthoplan.model import (
    MeshAsset,
    MeshProvenance,
    MeshUnits,
    SegmentedToothMesh,
    Stage,
    TimelineSettings,
    ToothDelta,
    ToothId,
    ToothLocalFrame,
    TreatmentPlan,
    TreatmentSettings,
    UploadedScan,
)

EXAMPLES_DIR = Path(__file__).resolve().parent
# Fixed timestamp so regenerating the examples does not churn the checked-in JSON.
FIXED_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def basic_plan() -> TreatmentPlan:
    """A minimal plan: a few stages, no scans, one movement that trips a cap."""
    return TreatmentPlan(
        id="example-basic",
        title="Synthetic example - basic staged plan",
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2),
                    ToothDelta(tooth=ToothId(value="21"), translate_x_mm=0.2),
                ],
            ),
            Stage(
                index=1,
                deltas=[
                    # 0.30 mm > the 0.25 mm default linear cap -> one finding.
                    ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.30),
                    ToothDelta(tooth=ToothId(value="21"), translate_y_mm=0.18),
                ],
            ),
        ],
    )


def segmented_plan() -> TreatmentPlan:
    """A plan exercising segmentation: a confirmed-units scan, a per-tooth mesh
    with an approximate local frame, and rotation values that stay tabular."""
    scan = MeshAsset(
        id="example-arch-scan",
        format="stl-binary",
        provenance=MeshProvenance.SYNTHETIC,
        units=MeshUnits.MM,
        vertex_count=3,
        face_count=1,
        created_at=FIXED_TS,
        reference="synthetic_arch.stl",
    )
    tooth_mesh = MeshAsset(
        id="example-tooth-11",
        format="stl-binary",
        provenance=MeshProvenance.SYNTHETIC,
        units=MeshUnits.MM,
        vertex_count=3,
        face_count=1,
        created_at=FIXED_TS,
        reference="synthetic_tooth_11.stl",
    )
    return TreatmentPlan(
        id="example-segmented",
        title="Synthetic example - segmented with approximate per-tooth frame",
        settings=TreatmentSettings(timeline=TimelineSettings(wear_interval_days=10)),
        scans=[UploadedScan(asset=scan, arch="maxillary", source="synthetic")],
        mesh_assets=[tooth_mesh],
        tooth_meshes=[
            SegmentedToothMesh(
                tooth=ToothId(value="11"),
                mesh_asset_id="example-tooth-11",
                source=MeshProvenance.SYNTHETIC,
                local_frame=ToothLocalFrame(
                    origin=(0.0, 0.0, 0.0),
                    axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                ),
            )
        ],
        stages=[
            Stage(
                index=0,
                deltas=[
                    ToothDelta(
                        tooth=ToothId(value="11"),
                        mesh_asset_id="example-tooth-11",
                        translate_x_mm=0.15,
                        rotate_rotation_deg=1.5,
                    )
                ],
            )
        ],
    )


def main() -> None:
    write_plan(basic_plan(), EXAMPLES_DIR / "basic_plan.json")
    write_plan(segmented_plan(), EXAMPLES_DIR / "segmented_plan.json")
    print("Wrote basic_plan.json and segmented_plan.json")


if __name__ == "__main__":
    main()
