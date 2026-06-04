# UI and Visualization Design

Visual representation is a primary product requirement for OpenSource Ortho. The interface must help users understand proposed tooth movement accurately without implying clinical approval.

## Visualization Contract

The UI must show what the system actually knows:

- display real or synthetic mesh geometry, not decorative stand-ins
- label whether geometry is patient-derived, imported, model-segmented, manual, or synthetic
- show current, planned, and staged positions in the same coordinate frame
- make cumulative movement visible across stages
- expose units for translations and rotations
- show data gaps near the affected visualization, especially missing roots, CBCT, occlusion, periodontal status, and clinician notes
- avoid colors or badges that imply safe, approved, cleared, or clinically acceptable

## Core Views

The first production-grade UI should include:

- stage timeline with scrubber and exact stage index
- before / current / planned overlay mode
- per-tooth movement table linked to the 3D selection
- displacement vectors and rotation indicators
- rule findings panel tied to highlighted geometry
- data-availability panel that remains visible during plan review
- exportable visual report with the same safety boundary language

## Accuracy Requirements

The viewer must not silently approximate away clinically relevant uncertainty.

- Mesh transforms must be derived from the `TreatmentPlan` stage data.
- Stage displays must use cumulative transforms, not just per-stage deltas.
- Coordinate frame names must be visible in developer/debug views.
- Any interpolation between stages must be labeled as visualization interpolation, not treatment data.
- Measurements must include units and source.
- Missing anatomical data must be visible when it affects interpretation.

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
- Heavyweight clinical/research host: 3D Slicer extension

The data contract should live in Python first so every UI consumes the same stage-frame representation.

