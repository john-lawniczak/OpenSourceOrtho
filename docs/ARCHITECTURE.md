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

The first UI prototype is a static browser workspace under `ui/`. It mirrors
the Python data contract but does not yet run backend STL inspection.

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

`ToothId`

- canonical FDI identity in Phase 1 (two-digit notation)
- `arch` is derived from the FDI quadrant, never stored separately, so the two can never contradict
- mixed numbering systems are rejected at plan creation rather than silently normalized

`CoordinateFrame`

- typed, named frame replacing the former free-form string
- declares axis semantics: `z` is the occlusogingival (vertical) axis; `x`/`y` span the horizontal plane
- per-tooth mesiodistal/buccolingual axes are unresolved at the global scan level, so tip/torque/rotation are not renderable in Phase 1

`MovementCaps`

- clinician-configurable per-stage caps held in an `AxisCaps` block (`default`)
- `per_tooth_overrides` is reserved so tooth-class-specific caps can be added later without changing the rule interface
- horizontal `linear_mm` caps the Euclidean magnitude of x/y movement; `intrusion_extrusion_mm` caps vertical movement separately
- default values are literature/vendor heuristics, not medical clearance
- caps are not evaluated until scan units are confirmed (see STL Upload)

`StageProgressFrame`

- cumulative tooth positions at a stage
- carries `rotation_renderable` and a crown-centroid pivot label
- data gaps attached for the UI
- designed so the UI does not recalculate treatment movement differently from the engine; transform composition lives in `planning/transforms.py`, and `viz` only consumes it

## STL Upload

The initial user upload should be an STL of an intraoral scan. STL contains surface geometry only. It does not contain roots, bone, periodontal status, occlusion dynamics, diagnosis, or CBCT anatomy.

That means the UI must show these data gaps. A surface scan can support crown-surface visualization and staged crown movement, but it cannot prove root position, bone safety, or periodontal suitability.

STL upload is metadata-only in Phase 1 (`orthoplan/io/stl_import.py`):

- mesh bytes are never stored in the serialized plan; only redacted metadata and an optional relative reference are kept
- absolute paths and directory structure (which often carry patient names) are stripped
- STL files carry no units, so units default to `unverified` and must be confirmed by the user before movement-cap evaluation runs
- a bounding-box sanity check can warn about implausible scale, but never infers units

## How The Plan Moves Teeth

A plan does not deform a tooth mesh. It applies rigid transforms to segmented tooth objects:

- translation along x/y/z in millimeters
- tip, torque, and rotation in degrees
- cumulative movement from stage 0 through the selected stage
- the visualization pivot is the crown centroid, an explicit visualization assumption and not a biomechanical claim about root position

Translation accumulates as a true vector sum (translation is commutative), so cumulative translation is geometrically correct. For example, if tooth 11 moves `0.2 mm` in stage 0 and `0.3 mm` in stage 1, the stage-1 frame shows `0.5 mm`.

Rotation is different. Summed Euler components (tip/torque/rotation) are not a composable rigid rotation, and converting them to a renderable transform requires per-tooth anatomical axes that the Phase 1 scan frame does not resolve. So frames report cumulative rotation values but flag `rotation_renderable=False`; a UI must not build a rotation matrix from a non-renderable pose. This is why `build_stage_progress_frames()` exists and why transform composition lives in `planning/transforms.py`.

## Movement Settings

Movement settings are guardrails, not clinical approval. Defaults should be conservative and configurable by the treating clinician.

Initial heuristic defaults (`AxisCaps`):

- linear movement: `0.25 mm` per stage (Euclidean magnitude of horizontal x/y movement)
- angular movement: `1.0 degree` per stage (tip and torque)
- rotation: `2.0 degrees` per stage
- intrusion/extrusion: `0.10 mm` per stage (vertical, evaluated separately)

These defaults are based on commonly cited clear-aligner staging ranges and should be treated as starting points for research tooling only. The software must never claim that a movement within these values is safe.

Timeline is an arithmetic projection, not a clinical estimate. Only inputs are stored (stage count comes from the plan; `wear_interval_days` defaults to 14). Duration is computed on demand in `planning/timeline.py` and always carries the caveat that the projection excludes refinements, compliance variation, clinical pauses, and clinician-directed changes.
