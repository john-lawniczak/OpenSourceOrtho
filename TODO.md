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

### Phase 17: Side-By-Side Setup Comparison And Live Restaging

Already in place: deterministic setup comparison/restage contracts, CLI output,
and a Review-side setup comparison panel with saved/captured baselines, live
restage updates, movement/control deltas, timeline changes, and JSON payloads.

Remaining implementation:

- Build a full side-by-side 3D workspace for current, generated, edited, and
  saved-version setups.
- Add per-stage visual diff controls that keep before/after/overlay views
  synchronized.
- Add explicit non-overwriting version promotion so a candidate setup can become
  the active plan only after user confirmation.
- Preserve provenance for every compared setup: generated, manual, saved
  version, restored version, or imported plan.
- Add focused UI/browser tests for comparison rendering, stage sync, live
  restage updates, and promotion behavior.

### Phase 18: Richer 3D Controls And Arch Response

Remaining implementation:

- Add direct controls for translation, intrusion/extrusion, rotation, crown tip,
  crown torque, and crown angulation.
- Add arch-form expansion/contraction controls with visible arch response
  proposals.
- Add editors for attachment/cut metadata, IPR/spacing, tooth locking, movement
  exclusions, and reviewed movement notes.
- Propose same-arch response adjustments that preserve contacts/spacing when
  possible, with deterministic warnings when the response cannot be assessed.
- Keep every control review-gated and provenance-labeled; no direct control
  should imply treatment approval or physical-use readiness.
- Add engine/UI tests for each control family and for fail-closed behavior when
  units, segmentation, roots, or reviewed anatomy are missing.

### Phase 19: Longitudinal Case-Bundle Outcomes

Already in place: contribution manifests, CLI registration, longitudinal scan
labels, validated sidecars, and benchmark readiness metrics for target setup,
tracking error, and refinement-prediction coverage.

Remaining implementation:

- Define numeric outcome-error metrics once consented before/progress/refinement/
  final STL scan bundles exist.
- Add target-setup error reports comparing intended setup geometry against final
  or refinement setup geometry.
- Add tracking-error reports comparing planned stage positions against progress
  scans where stage timing is known.
- Add refinement-prediction reports that separate planned refinements from
  unplanned refinements and missing/unknown outcomes.
- Expand non-PHI fixture coverage without committing identifiable scans or
  proprietary treatment exports.
- Document benchmark interpretation so sparse community data does not get
  overstated as clinical accuracy.

## Cross-Cutting Backlog

- Add richer provider-native AI streaming adapters and tool-style plan actions
  while preserving explicit egress consent and advisory-only wording.
- Harden export/audit trails around setup comparison, direct-control edits,
  restaging, and print-package generation.
- Continue broadening real-scan, non-PHI smoke coverage for segmentation,
  rendering, setup comparison, shell QA, and longitudinal benchmarks.
- Keep README, architecture docs, safety docs, and glossary terms synchronized
  whenever user-facing capabilities or data-contribution standards change.
