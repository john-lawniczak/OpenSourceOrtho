# Next Context Implementation Plan

This is a temporary working plan for the next implementation chat. Its purpose is to let the next context window start coding without re-discovering priorities.

## North Star

Build OpenSource Ortho into a safety-boundary-first, visually accurate, composable treatment-planning research toolkit for clear-aligner workflows.

The product should let a user upload an STL intraoral scan, create or inspect a staged `TreatmentPlan`, configure movement caps, view data gaps, and scrub through estimated tooth movement in a modern, straightforward UI.

The system must never imply clinical approval, diagnosis, treatment suitability, or root/bone safety from STL surface data alone.

## Long Strategy

### Phase 0 - Project Foundation

Status: mostly complete.

Goals:

- keep root docs minimal and move detailed docs to `docs/`
- preserve safety boundary as architecture
- keep OpenAI and Claude Code agent instructions aligned
- keep file sizes and module ownership under control
- keep a living source ledger for external references

Exit criteria:

- tests pass
- maintainability check passes
- dev-history hook writes to `docs/Dev_history.md`
- docs explain the STL-to-plan flow clearly

### Phase 1 - Full Data Model Workflow

This is the next coding target.

User journey:

1. User starts a new plan.
2. User uploads an STL file.
3. App records mesh metadata and provenance.
4. App creates a `TreatmentPlan` draft.
5. User declares what data is available.
6. User configures movement caps.
7. User defines or imports staged tooth movement.
8. App estimates timeline from stage count and aligner wear interval.
9. App builds cumulative progress frames for visualization.
10. App evaluates deterministic movement-cap findings.
11. UI shows a review screen with plan summary, stage timeline, movement settings, and data gaps.

Backend objects to complete:

- `MeshAsset`
- `UploadedScan`
- `PlanTimeline`
- `TreatmentPlan`
- `Stage`
- `ToothDelta`
- `ToothId`
- `DataAvailability`
- `MovementCaps`
- `TreatmentSettings`
- `StageProgressFrame`

Implementation tasks:

- add `orthoplan/model/assets.py` for uploaded mesh metadata
- add `orthoplan/model/timeline.py` for stage-count and wear-interval estimates
- expand `TreatmentPlan` to reference uploaded scans and timeline settings
- add JSON serialization helpers for import/export
- add STL metadata extraction in `orthoplan/io/stl_import.py`
- add synthetic STL fixture generation or checked-in tiny fixture metadata
- add CLI commands:
  - `orthoplan new-plan`
  - `orthoplan inspect-stl`
  - `orthoplan plan-summary`
- add deterministic tests for each object

Important constraints:

- do not require patient data for tests
- do not implement diagnosis or treatment approval
- treat STL as surface-only crown geometry
- keep movement caps configurable
- make all units explicit

Exit criteria:

- user can inspect an STL and create a draft plan object
- plan can serialize to JSON and load back losslessly
- stage timeline estimate is deterministic and tested
- data gaps are visible in the serialized output
- movement caps are included in plan settings
- `pytest` and maintainability checks pass

### Phase 2 - UI Prototype For Data Model Workflow

Goal: build the first modern, straightforward UI journey around the Phase 1 model.

Recommended stack:

- keep Python package as the core engine
- add a lightweight web app only after the data contract is stable
- candidate frontend: React + TypeScript + Vite
- candidate 3D layer: Three.js
- candidate UI components: a small custom design system with lucide icons

First UI screens:

1. New Plan
   - upload STL
   - plan title
   - numbering system
   - clear safety/data limitation note

2. Data Availability
   - toggles for intraoral scan, segmented teeth, roots, CBCT, periodontal status, occlusion scan, photos, radiographs, clinician notes
   - visible explanation that disabled data cannot be inferred

3. Movement Settings
   - sliders or numeric inputs for linear, angular, rotation, and intrusion/extrusion caps
   - units visible beside every control
   - defaults described as configurable heuristics, not safety approval

4. Stage Builder
   - table of teeth and stage deltas
   - add/remove stage controls
   - per-tooth movement input fields
   - cap warnings inline

5. Timeline Review
   - estimated aligner count from stage count
   - wear interval setting, default configurable
   - estimated duration shown as a range or configured estimate

6. Progress Preview
   - stage scrubber
   - current/planned/overlay modes
   - data gaps visible near viewer
   - per-tooth movement table linked to selected tooth

Design direction:

- operational, calm, dense, inspectable
- no marketing hero page
- no decorative gradients or visual noise
- stable left-to-right workflow
- primary actions are clear and predictable
- 3D geometry is the focus once uploaded
- warning language is observational, not verdict-like

Exit criteria:

- user can complete a draft plan workflow without reading docs
- UI state maps directly to Python/JSON data contracts
- controls are modern but restrained
- no text overlap on desktop or mobile
- data gaps are always visible during review

### Phase 3 - Mesh IO and Segmentation Workflow

Goals:

- robust STL import/export
- mesh validation and repair warnings
- manual segmentation placeholders
- imported segmentation support
- no ML segmentation until license/model/data constraints are resolved

Tasks:

- use `trimesh` or Open3D after license/dependency review
- extract mesh units, bounding box, vertex/face counts, normals status, watertight status
- add warnings for scale ambiguity and malformed meshes
- support per-tooth mesh asset references
- keep all mesh provenance explicit

Exit criteria:

- uploaded STL metadata is available to plan and UI
- malformed mesh findings are deterministic
- test fixtures are synthetic

### Phase 4 - Deterministic Evaluation Expansion

Goals:

- rule engine grows before model advisory logic
- every finding remains linted
- data gaps stay visible

Rules to add:

- stage index consistency
- duplicate tooth movement
- missing segmentation
- movement caps per axis
- estimated timeline outliers
- missing roots/CBCT when movement type could be root-sensitive
- coordinate frame mismatch
- unsupported numbering system mismatch

Exit criteria:

- rules run without any model provider
- findings are stable and testable
- warning findings include data gap and clinician question

### Phase 5 - Model Advisory Layer

Goals:

- OpenAI first adapter remains provider-neutral
- Claude Code adapter remains optional
- model output cannot bypass linting

Tasks:

- define structured model response schema
- parse model advisories into `Finding`
- reject unlintable findings
- inject `DataAvailability`, `MovementCaps`, and safety boundary into prompt
- add fixtures for banned output

Exit criteria:

- model advisory layer can be disabled
- no generated finding renders without linting
- advisory findings are prefixed and provenance-tagged

### Phase 6 - Visualization Fidelity

Goals:

- accurate progress representation becomes the center of the product
- UI never recalculates movement differently from backend

Tasks:

- convert `StageProgressFrame` to frontend JSON
- build transform matrices from cumulative poses
- add before/current/planned/overlay modes
- add displacement vectors
- add selected-tooth detail panel
- add screenshot/exportable report path

Exit criteria:

- progress scrubber is deterministic
- UI display matches serialized frame data
- missing anatomy remains visible in visual review

### Phase 7 - Packaging, Examples, and Public Readiness

Goals:

- make repo usable by contributors
- maintain safety posture
- avoid patient data

Tasks:

- add synthetic example plans
- add CLI walkthrough
- add screenshots or generated fixture images
- add contribution guide
- add dependency license audit
- add CI

Exit criteria:

- new contributor can run tests and inspect an example plan
- no patient data exists in repo
- license assumptions are documented

## Immediate Next Implementation Checklist

Start here in the next context window:

1. Add `orthoplan/model/assets.py`.
2. Add `orthoplan/model/timeline.py`.
3. Extend `TreatmentPlan` with scan assets and timeline.
4. Add `orthoplan/io/stl_import.py` with metadata-only STL inspection.
5. Add JSON serialization helpers.
6. Add CLI commands for STL inspection and plan creation.
7. Add tests for assets, timeline, serialization, and CLI.
8. Add a small UI planning contract if frontend is started.

## Suggested Data Model Shape

`MeshAsset`

- `id`
- `path`
- `format`
- `provenance`
- `vertex_count`
- `face_count`
- `bounds_mm`
- `units`
- `created_at`
- `sha256`

`UploadedScan`

- `asset`
- `arch`
- `source`
- `notes`

`PlanTimeline`

- `stage_count`
- `wear_interval_days`
- `estimated_duration_days`
- `estimated_duration_weeks`
- `retainer_phase_included`

`TreatmentPlan`

- `id`
- `title`
- `numbering_system`
- `data`
- `settings`
- `timeline`
- `scans`
- `stages`

## UI Data Controls For Phase 1

Movement cap controls:

- linear movement per stage, mm
- tip/torque per stage, degrees
- rotation per stage, degrees
- intrusion/extrusion per stage, mm
- wear interval per stage, days
- numbering system

Data availability controls:

- intraoral scan
- segmented teeth
- roots
- CBCT
- periodontal status
- occlusion scan
- photos
- radiographs
- clinician notes

Timeline display:

- number of stages
- estimated aligners
- wear interval
- estimated duration
- data gaps affecting confidence

## Modern UI Principles For This Product

- Use a wizard-like journey for first plan creation, then a dense review workspace.
- Keep the first screen useful, not promotional.
- Use real geometry whenever available.
- Use icons for upload, view modes, stage navigation, warnings, settings, export, and reset.
- Use toggles for data availability.
- Use numeric inputs/sliders for movement caps.
- Use tabs or segmented controls for current/planned/overlay views.
- Use tables for tooth-level movement because users need precision.
- Avoid large decorative cards and marketing composition.
- Keep warnings close to the data they describe.
- Make unavailable data visually obvious without alarming verdict language.

## Questions To Resolve Later

- Should the first UI be web-first or Python desktop-first?
- Should `trimesh` be added immediately for STL metadata, or should we start with a tiny internal binary/ascii STL inspector?
- What tooth-numbering system should be default for the intended first users?
- How should manual segmentation be represented before we have real segmentation tooling?
- Should timeline defaults assume 7-day, 10-day, or 14-day wear intervals?
- What minimum synthetic mesh fixture is enough for early UI development?

