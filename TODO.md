# TODO

This file tracks only work that still needs implementation. Completed phases,
historical status notes, and already-shipped reference items belong in git
history, release notes, or the relevant docs instead of this active list.

## Product Goal

OpenSource Ortho is working toward functional coverage of a modern
clear-aligner planning workflow while preserving an explicit safety boundary:
scan intake, segmentation, target setup, side-by-side setup comparison, direct 3D
controls, live restaging, root/bone-aware review, manufacturing-oriented QA,
progress/refinement records, and retention handoff.

Generating geometry never means diagnosis, clinical approval, treatment
clearance, or that physical use is safe. Printing, fit, materials,
post-processing, and any physical use remain the user's own responsibility and
risk. Every output must keep its review tier, manufacturing-readiness status,
provenance, and unresolved data gaps clearly labeled.

## Active Roadmap

The current phase-sized work focuses on closing the gap between strong engine
components and an ordinary user's end-to-end workflow. See
[docs/NEW_USER_WORKFLOW_GAPS.md](docs/NEW_USER_WORKFLOW_GAPS.md) for the supporting
assessment.

### Phase 13: Unified Intake Readiness

- Add a typed readiness contract covering each STL, bite record, CBCT/DICOM
  record, segmentation, registration, and reviewed-anatomy dependency.
- Separate record readiness, plan consistency, artifact readiness, and physical
  validation in the API and UI.
- Show actionable blockers with direct links to the control that resolves each
  one.
- Add fixtures for complete, partial, mislabeled, wrong-scale, noisy, and
  conflicting record sets.
- Add an end-to-end test for a user's own uploaded records, not only the bundled
  sample.

### Phase 14: Segmentation Correction Workspace

- Add split, merge, brush/lasso reassignment, artifact hiding, and visual
  missing-tooth controls for proposed crown regions.
- Add undo/redo, before/apply comparison, per-tooth quality state, and named
  reviewed segmentation versions.
- Persist every correction with input hashes and provenance.
- Benchmark proposal quality and human correction time on licensed non-PHI
  real-scan cases.

### Phase 15: CBCT Companion Integration

- Add local DICOM-directory intake with explicit PHI and storage-location
  disclosure.
- Define and implement a reviewed anatomy/landmark manifest roundtrip with a
  trusted local viewer such as 3D Slicer.
- Add visible STL-to-CBCT registration overlays and numeric quality review.
- Keep volume-derived masks, automatic registration, and imported anatomy
  untrusted until deterministic gates and explicit acceptance succeed.
- Expand reviewed open-volume and registration fixtures.

### Phase 16: Structured AI Proposals and Audit Trail

- Let configured models propose constrained plan actions as structured,
  non-applied patches rather than directly mutating a plan.
- Show before/after diffs, provider/model/context provenance, and deterministic
  re-evaluation before Apply/Reject.
- Route all generated findings and user-facing action explanations through the
  existing lint boundary.
- Export an audit history for chat requests, proposed actions, acceptance,
  restaging, comparison, and print-package generation.

### Phase 17: Durable Cases and Distribution

- Unify browser storage, server case records, mesh assets, segmentation
  versions, and plan versions into an autosaved, recoverable case lifecycle.
- Add portable backup/import, schema migrations, record hashes, and explicit
  local-data location controls.
- Add dependency diagnostics and a nondeveloper installation/distribution path;
  keep heavyweight mesh/CBCT components optional.
- Add recovery, migration, and case-roundtrip regression tests.
- Expand artifact-inventory and geometry-QA reporting without implying physical
  fit, material validation, clinical authorization, or safe physical use.

## Cross-Cutting Backlog

- Add richer provider-native AI streaming adapters and tool-style plan actions
  while preserving explicit egress consent and advisory-only wording.
- Harden export/audit trails around setup comparison, direct-control edits,
  restaging, and print-package generation.
- Continue broadening real-scan, non-PHI smoke coverage for segmentation,
  rendering, setup comparison, shell QA, and longitudinal benchmarks.
- Track intake failures, segmentation correction burden, registration-gate
  distributions, export blockers, and case-recovery success in validation
  reports.
- Keep README, architecture docs, safety docs, and glossary terms synchronized
  whenever user-facing capabilities or data-contribution standards change.
