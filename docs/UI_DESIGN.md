# UI and Visualization Design

Visual representation is a primary product requirement for OpenSource Ortho. The interface must help users understand proposed tooth movement accurately without implying approval.

## Visualization Contract

The UI must show what the system actually knows:

- display real or synthetic mesh geometry when available; otherwise make schematic proxies unmistakably schematic
- label whether geometry is patient-derived, imported, model-segmented, manual, or synthetic
- show current, planned, and staged positions in the same coordinate frame
- make cumulative movement visible across stages
- expose units for translations and rotations
- show data gaps near the affected visualization, especially missing roots, CBCT, occlusion, periodontal status, and treatment notes
- avoid colors or badges that imply safe, approved, cleared, or acceptable

## Core Views

The UI supports distinct product surfaces, switched by a single **Clinician /
Guided** toggle that stays on the left in both modes (there is no separate
in-content "technician view" button):

- **Guided wizard** (the default, primary surface) for non-technical users: a
  step-by-step flow with a progress rail of six chips - **Upload → Teeth & time →
  Details → Review → 3D preview → Print / send**. One step is visible at a time
  with Back/Next. It acknowledges limits in plain language, lets the user choose
  which teeth move (excluded teeth become fixed) and the tray-wear duration,
  animates the plan in 3D, and exports printable files. The heavy singletons (3D
  viewer, AI box, upload control) are single instances relocated into the active
  step, so there is never a second WebGL context.
- **Clinician review** for professional users: staged movement authoring, records,
  clinical controls, mesh rendering, rule findings, optimized staging, print
  metadata, and plan JSON.
- **Sample test case**: a fully isolated demonstration that reuses the guided
  wizard (same chips/panels) pre-filled with demo data. Entering it snapshots the
  user's working state and restores it on exit, and it carries its own "Exit
  sample" control (the mode toggle is hidden inside it) so the demo can never leak
  into or be left in the user's own editors.
- **Plan AI review** for both workflows: scoped chat over the current plan,
  findings, data gaps, and timeline. The provider selector and a session-only
  API-key field are surfaced directly (with provider-specific, plain-language
  help; the key field is hidden for the no-key local helper) so enabling a real
  model is discoverable. It must label the connector and context scope, keep raw
  API keys out of persisted plan data, and never present AI text as diagnosis or
  approval.

The first production-grade clinician UI should include:

- stage timeline with scrubber and exact stage index
- before / current / planned overlay mode
- per-tooth movement table linked to the 3D selection
- displacement vectors and rotation values; rendered rotation only with trusted anatomical frames
- rule findings panel tied to highlighted geometry
- data-availability panel that remains visible during plan review
- acquisition advisor panel showing what missing data would change or unlock
- exportable visual report with the same safety boundary language
- auditable chat panel with local default behavior and explicit external
  connector/context selection
- light and dark themes with equal readability for controls, findings, and the
  3D viewer

## Accuracy Requirements

The viewer must not silently approximate away measurement-relevant uncertainty.

- Mesh transforms must be derived from the `TreatmentPlan` stage data.
- Stage displays must use cumulative transforms, not just per-stage deltas.
- Coordinate frame names must be visible in developer/debug views.
- Any interpolation between stages must be labeled as visualization interpolation, not treatment data.
- Measurements must include units and source.
- Missing anatomical data must be visible when it affects interpretation.
- Approximate PCA tooth frames are metadata/debug aids, not enough to render tip, torque, or long-axis rotation.
- AI chat must consume a declared context package and disclose when requested
  information is absent from that package.

## Design Tone

This is an operational planning tool, not a marketing site. The UI should be dense, calm, and inspectable:

- restrained color use
- predictable toolbars and panels
- stable 3D viewport layout
- icon buttons for camera/view tools
- compact tables for tooth-level data
- no decorative visual effects that compete with geometry

## Implementation Direction

Use a proven 3D stack for mesh display. Good candidates:

- Python-first prototype: PyVista/VTK
- Web UI: Three.js with explicit transform and measurement layers
- Heavyweight research host: 3D Slicer extension

The data contract should live in Python first so every UI consumes the same stage-frame representation.
