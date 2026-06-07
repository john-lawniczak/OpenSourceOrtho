# Architecture

OpenSource Ortho is a Python-first planning and visualization toolkit. The first milestone is not a polished production product; it is a clean, inspectable engine that can import dental meshes, represent staged movement, check configured movement caps, and feed an accurate UI.

## Simple Flow

1. The user uploads an intraoral-scan mesh, usually an STL file.
2. The mesh is imported and labeled with provenance: patient-derived, imported, manual, model-generated, or synthetic.
3. Teeth are segmented into individual tooth meshes. The first implementation should be manual or imported segmentation; machine learning can come later.
4. A `TreatmentPlan` stores each stage. Each `Stage` contains `ToothDelta` values for individual teeth.
5. The planning layer checks each stage against user-configured `MovementCaps`.
6. The visualization layer converts the plan into cumulative `StageProgressFrame` objects.
7. The UI renders current, staged, and planned positions from those cumulative frames.
8. Deterministic rules run first. Model providers such as OpenAI or Claude Code may add advisory findings, but all findings pass through `lint_finding()`.
9. Optional print-export settings record intended file format, delivery email, materials, acknowledgement, and export blockers; `print-package` can generate stage proxy STL files, a manifest, zip package, and email draft.

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

The browser UI never reimplements the engine. `orthoplan/api.py` exposes pure entry points, and `orthoplan/server.py` serves them: `POST /api/evaluate` for findings/frames, and `POST /api/print-package` (`print_package_payload`, reusing `export_print_package`) which returns a base64 zip of stage proxy STLs + manifest and an `.eml` draft for the guided Print / send step. The UI sends plan-shaped JSON and renders the returned findings, data gaps, data-gap actions, timeline projection, and `StageProgressFrame` data verbatim - so there is exactly one source of truth for movement and policy. The 3D progress viewer (Three.js, vendored) renders schematic per-tooth proxies from those frames; it draws rotation only where the engine marks it renderable. PCA `tooth_frames` are exposed as approximate metadata but do not make rotation renderable.

The UI is a static browser workspace under `ui/`. It opens by default into a
guided, six-step wizard (`ui/guided.js`) for non-technical users; the dense
Clinician workspace is one toggle away. A self-contained **Sample test case**
(`ui/sample.js`) reuses the guided wizard with demo data and snapshots/restores
the user's working state so it stays isolated. The UI mirrors the Python data
contract but does not run backend STL inspection itself.

The local development server can also serve registered per-tooth STL meshes from a
local mesh workspace. Plan JSON still does not contain mesh bytes; it contains
`mesh_asset_id` links. `orthoplan register-mesh` copies an STL into a local
workspace registry, and `/api/mesh/<mesh_asset_id>` serves only registered files
under that workspace. The UI uses `render_meshes` links from `evaluate_plan()` to
load real tooth meshes when available and falls back to schematic proxies when a
mesh is missing.

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

- user-configurable per-stage caps held in an `AxisCaps` block (`default`)
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

Approximate crown-surface PCA frames are not enough to change that flag. A future real-mesh
orientation path must supply non-approximate anatomical frames or another validated frame
source before rotation can be rendered.

For local real-mesh visualization, `planning/mesh_transform.py` can transform externally
supplied per-tooth vertices by cumulative translation while preserving the same rotation
honesty rule. The server/UI path uses the same stage frames; real STL meshes are visual
geometry, not a different planning engine.

## Plan Generation

`planning/generate.py` turns the best available target into cap-respecting staging
by reusing the existing optimizer (`planning/optimizer.py`) - it never re-implements
staging or caps. Target resolution is, in order: authored movement; a
**landmark-derived** plan (per-tooth crown landmarks → real arch-form deviation
targets + arch-length/space analysis in `planning/arch_analysis.py`, assembled with
IPR, attachments, and approximate collision bounds in `planning/landmark_plan.py`);
a geometry-derived arch-form fit over visible segmented crowns
(`planning/arch_form.py`); or a labeled educational template. It has no model calls.

The top-level `generation.py` gateway composes the deterministic generator with
`run_rules` validation, a deterministic correctness review, and an optional
consent-gated model review reusing `evaluation/advisory.py`. The UI consumes the
returned staged plan through the same stage-frame contract as everything else; it
does not re-stage. See [SAFETY.md](SAFETY.md) for the boundary.

The correctness review emits explicit named **checks**, each with a pass/fail and
a severity. Gate checks (`caps-respected`, `fixed-teeth-unmoved`,
`exclusions-respected`, `targets-reached`, `stages-contiguous`) decide the verdict
(`CONSISTENT`/`ISSUES`/`NOT_APPLICABLE`, never an approval). `scale-confirmed` is a
warning check and `collisions-checked` is informational (it reports when the
overlap check is vacuous because no segmented teeth exist). `targets-reached`
regression-checks that the staged plan's cumulative movement actually reaches the
requested target, so a staging bug cannot pass silently.

## Plan Versions

`cases.py` stores a `CaseStore` of `CaseRecord`s, each holding ordered
`PlanVersion` snapshots (full plan JSON + content hash + engine version + note).
A "case" groups versions of one plan; the default case id is the plan id.
`case_api.py` wraps this in dict-in/dict-out functions used by both the server
(`POST /api/plan/version`, `GET /api/cases`, `GET /api/cases/<case_id>`) and the
CLI (`case-save`, `case-list`, `case-versions`). The store path defaults to
`.orthoplan-cases.json` and is overridable via `ORTHOPLAN_CASE_STORE`. The UI's
Versions panel saves snapshots and restores any version back into the editor.

## Handoff Reports

`orthoplan report PLAN.json` emits a deterministic handoff artifact. The report includes the
engine version, canonical plan hash, stable evaluation hash, input metadata, findings,
data-gap actions, timeline, progress frames, review metadata, and a report hash. It can also
include an optional HMAC-SHA256 signature. It does not include mesh bytes. The goal is
reproducible review: the artifact ties inputs to engine behavior and makes provenance auditable
without claiming approval.

## Print Export Architecture

`TreatmentSettings.print_export` records export intent: format (`stl`/`3mf`), optional
delivery email, model material, thermoforming material, post-processing notes, and a safety
acknowledgement. `orthoplan.printing.build_print_export_status()` turns that intent into a
readiness object with blockers and planned artifact filenames.

`orthoplan print-package PLAN.json --out DIR` generates stage proxy STL files from the current
plan frames, a manifest, an optional deterministic zip package, and an optional `.eml` email
draft. The manifest records the engine version, canonical plan hash, stage-frame hash,
per-artifact SHA-256 hashes, byte sizes, blockers, and geometry-source metadata. When a tooth
has linked segmented mesh bounds, the generated proxy is sized from those bounds; otherwise it
is explicitly labeled as schematic proxy geometry. These are objective geometry outputs from
the supplied plan data. Material choice, printing, post-processing, and any physical use are
the user's responsibility and risk.

The next print-geometry phase should package intentionally supplied mesh bytes and transform
actual per-tooth vertices instead of bounded proxy solids.

## Acquisition Advisor

`orthoplan/evaluation/acquisition.py` computes deterministic marginal data-acquisition
impact. For each applicable missing modality, it builds a counterfactual plan with only that
availability flag filled, reruns `run_rules()`, and diffs findings/data gaps. The output says
which absence-of-data findings would clear, which suppressed checks would run, and which gap
entries would close. It never predicts what the acquired data would show.

## Parallel Agent Review

Parallel LLM/sub-agent review can be useful as an optional second-opinion layer: one agent may
summarize geometric consistency, another may inspect data gaps, another may review print/export
readiness, and another may produce handoff questions. This is not necessary for the core
application to be correct, because deterministic rules remain the source of truth. Any
agent-generated output must enter as advisory text, pass the same lint/quarantine boundary, and
must never suppress, overwrite, or weaken deterministic findings.

## Movement Settings

Movement settings are guardrails, not approval. Defaults are configurable.

Initial heuristic defaults (`AxisCaps`):

- linear movement: `0.25 mm` per stage (Euclidean magnitude of horizontal x/y movement)
- angular movement: `1.0 degree` per stage (tip and torque)
- rotation: `2.0 degrees` per stage
- intrusion/extrusion: `0.10 mm` per stage (vertical, evaluated separately)

These defaults are based on commonly cited clear-aligner staging ranges and should be treated as starting points for research tooling only. The software must never claim that a movement within these values is safe.

Timeline is an arithmetic projection, not an outcome estimate. Only inputs are stored (stage count comes from the plan; `wear_interval_days` defaults to 14). Duration is computed on demand in `planning/timeline.py` and always carries the caveat that the projection excludes refinements, compliance variation, pauses, and user-directed changes.
