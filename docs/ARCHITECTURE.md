# Architecture

OpenSource Ortho is a Python-first planning and visualization toolkit. The first milestone is not a polished clinical product; it is a clean, inspectable engine that can import dental meshes, represent staged movement, check configured movement caps, and feed an accurate UI.

## Simple Flow

1. The user uploads an intraoral-scan mesh, usually an STL file.
2. The mesh is imported and labeled with provenance: patient-derived, imported, manual, model-generated, or synthetic.
3. Teeth are segmented into individual tooth meshes. The first implementation should be manual or imported segmentation; machine learning can come later.
4. A `TreatmentPlan` stores each stage. Each `Stage` contains `ToothDelta` values for individual teeth.
5. The planning layer checks each stage against clinician-configured `MovementCaps`.
6. The visualization layer converts the plan into cumulative `StageProgressFrame` objects.
7. The UI renders current, staged, and planned positions from those cumulative frames.
8. Deterministic rules run first. Model providers such as OpenAI or Claude Code may add advisory findings, but all findings pass through `lint_finding()`.

## Language and Stack

The current scaffold is Python 3.11+.

Python is a good first language here because:

- dental mesh and medical-imaging libraries are mature in Python
- Pydantic gives us explicit, serializable plan objects
- PyVista/VTK and Open3D can support early visualization and mesh processing
- later web UIs can consume the same JSON frame contract

The likely future split:

- Python: data model, IO, planning, evaluation, CLI, test fixtures
- Three.js or VTK/PyVista: interactive 3D visualization
- Optional 3D Slicer extension: heavyweight dental/CBCT workflow integration

## Core Objects

`TreatmentPlan`

- plan ID and title
- numbering system such as FDI, Universal, or Palmer
- `DataAvailability` manifest
- staged movement list
- movement settings

`Stage`

- one aligner-style step
- list of per-tooth movement deltas

`ToothDelta`

- tooth identity
- arch
- translation in millimeters
- rotation in degrees
- coordinate frame
- movement source

`MovementCaps`

- clinician-configurable per-stage caps
- default values are literature/vendor heuristics, not medical clearance
- rules compare stage deltas to these caps

`StageProgressFrame`

- cumulative tooth positions at a stage
- data gaps attached for the UI
- designed so the UI does not recalculate treatment movement differently from the engine

## STL Upload

The initial user upload should be an STL of an intraoral scan. STL contains surface geometry only. It does not contain roots, bone, periodontal status, occlusion dynamics, diagnosis, or CBCT anatomy.

That means the UI must show these data gaps. A surface scan can support crown-surface visualization and staged crown movement, but it cannot prove root position, bone safety, or periodontal suitability.

## How The Plan Moves Teeth

A plan does not deform a tooth mesh. It applies rigid transforms to segmented tooth objects:

- translation along x/y/z in millimeters
- tip, torque, and rotation in degrees
- cumulative movement from stage 0 through the selected stage

For example, if tooth 11 moves `0.2 mm` in stage 0 and `0.3 mm` in stage 1, the stage-1 visualization frame shows `0.5 mm` cumulative movement. This is why `build_stage_progress_frames()` exists.

## Movement Settings

Movement settings are guardrails, not clinical approval. Defaults should be conservative and configurable by the treating clinician.

Initial heuristic defaults:

- linear movement: `0.25 mm` per stage
- angular movement: `1.0 degree` per stage
- rotation: `2.0 degrees` per stage
- intrusion/extrusion: `0.10 mm` per stage

These defaults are based on commonly cited clear-aligner staging ranges and should be treated as starting points for research tooling only. The software must never claim that a movement within these values is safe.

