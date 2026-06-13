# TODO

## Product goal

The browser workspace turns uploaded STL scans, and reviewed CBCT-derived anatomy
when present, into reproducible staged geometry and 3D-printable model/shell
artifacts. The north star is functional coverage of the modern clear-aligner
treatment-system workflow: scan intake, segmentation, target setup, side-by-side
setup comparison, direct 3D controls, live restaging, root/bone-aware review,
manufacturing-oriented QA, progress/refinement records, and retention handoff.
Safety posture is unchanged and fail-closed: generating geometry never means
diagnosis, clinical approval, treatment clearance, or that physical use is safe.
Printing, fit, materials, post-processing, and any physical use remain the user's
own responsibility and risk. Every output must keep its review tier,
manufacturing-readiness status, and unresolved data gaps clearly labeled.

## Current status on `feat/v1.2`

- Durable STL/CBCT intake, case storage, provenance, and review tiers
  (`stl-only`, `enhanced-records`, `cbct-attached`, `root-bone-aware`).
- STL surface planning with scale-gated millimeter checks, auto-segmentation +
  review UI, per-tooth fragment rendering, shared-engine findings, and
  surface-gap reports.
- Reviewed per-tooth print/export: real vertices only for reviewed segmentation,
  labeled proxy fallback otherwise, with plan/frame/findings/fragment hashes.
- Local DICOM metadata intake (PHI-stripped, no volume bytes) plus 3D Slicer
  handoff.
- STL-to-CBCT registration model with fail-closed acceptance gating.
- Reviewed CBCT-derived anatomy models for roots, axes, and bone with
  accept/correct/reject review status.
- Root/bone-aware review checks with `cannot assess` behavior when trusted
  anatomy is unavailable.
- Browser-to-mobile case-review handoff with opaque, edit-locked payloads,
  links, QR codes, and deep links.
- Printable aligner-shell generation for reviewed real geometry, including
  sheet thickness, optional trusted-axis trim, shell hashes, and model-only
  fail-closed fallback.
- Manufacturing-readiness QA for the pure-Python shell path: degenerate triangle
  cleanup, watertightness, connected components, rim closure, inner/outer
  clearance, thickness distribution, printer tolerance metadata, and
  `CONSISTENT` / `ISSUES` / `NOT_APPLICABLE` verdicts in API/export manifests
  (self-intersection/nonmanifold detection is covered by the real engine below).
- Root-aware movement for trusted reviewed root geometry and long axes; otherwise
  unchanged crown-centroid visualization output.
- Adjacent same-arch collision/IPR review using bbox prefiltering plus capped
  representative surface samples, with bbox fallback when samples are absent.
- Synthetic validation benchmark report for segmentation Dice/IoU, movement
  error, collision/IPR precision-recall, and shell thickness error.
- Printer XY/Z compensation baked into exported shell geometry (not metadata
  only), real per-facet STL normals, and shell QA (readiness verdict, applied
  compensation, per-stage watertight/thickness/self-intersection, skip reasons)
  surfaced in the guided and technician print UIs.
- Real triangle-triangle self-intersection engine (Möller narrow phase behind a
  spatial-grid broad phase) and nonmanifold-edge detection replacing the
  box-overlap approximation, per-artifact `failed_checks` explanations, and an
  independent analytic known-good oracle (closed-form slab volume) plus synthetic
  messy fixtures.
- Optional Open3D robust shell backend now runs in a dedicated CI lane, repairs
  messy meshes, applies distance-field offset correction, and records validation
  metrics against messy non-PHI and independent full-arch fixtures.
- In-app AI assistant now has bounded conversation memory, incremental message
  rendering, Enter-to-send, provider/model split with per-provider model memory,
  connector model catalogs, custom self-hosted model IDs, and per-request
  credential/PHI-share gating. Streaming-capable connectors now use an SSE chat
  path with a non-streaming JSON fallback.
- Benchmark reports now include metric deltas, reviewed non-PHI corpus metadata
  for the bundled Sample Test Case, messy-shell metrics, and sampled-vs-triangle
  collision/IPR distance metrics.
- Reviewed segmented tooth mesh assets are automatically resolved from the local
  mesh workspace for full triangle-level collision/IPR checks; unreviewed or
  missing geometry still fails closed to sampled/bbox checks.
- Learned ONNX segmentation now includes conservative contact-island label repair
  plus learned-vs-heuristic benchmark metrics on the Phase 13/16 synthetic corpus;
  the heuristic/hybrid backend remains the no-dependency fallback whenever the
  optional ONNX runtime or user-supplied weights are unavailable.
- Raw CBCT volume masks can feed proposed root centerlines, tooth axes, and
  alveolar-bone records into the reviewed-anatomy pipeline as `PROPOSED` only.
  Open3D ICP has an explicit auto-registration proposal wrapper with quality
  metrics and human acceptance gating; synthetic volume benchmarks and fail-closed
  tests prove unaccepted/rejected/proposed anatomy never becomes trusted.
- CBCT-to-reviewed-anatomy V1 is wired through the local UI/API: after attaching
  CBCT/DICOM and registering an STL scan, a reviewer can import local sparse mask
  JSON, create proposed roots/axes/bone records, and accept/correct/reject those
  objects through the reviewed-anatomy gate.
- Guided "Review your plan" step now leads with a review dashboard: an at-a-glance
  verdict (`ready` / `needs-review` / `cannot-assess`) plus edit-diff,
  warnings, root/bone, and print-readiness cards and 3D overlay chips. Only
  `warning`-severity findings count as blocking warnings; `info`/`notice` context
  (e.g. the healthy-plan `root-bone-context` info finding and skipped-check
  notices) never flips the verdict or fabricates overlay highlights.
- Phase 19 first slice: contribution manifests now support longitudinal scan
  labels (`initial`/`progress`/`refinement`/`final`), per-file arch inference
  from standard filenames, validated `plan-summary.json` sidecars, outcome-notes
  hashing, and CLI/tests for privacy-safe case bundles.
- Phase 19 benchmark layer: `validation-benchmark` now emits a
  `longitudinal-data` component for target-setup readiness, tracking-error
  readiness, refinement-prediction readiness, and plan-context coverage from
  consented/non-PHI case-bundle manifests.
- Phase 17 first slice: deterministic setup comparison and live-restage preview
  contracts now power a Review-side setup comparison panel with saved/captured
  baselines, live restage updates, movement/control deltas, timeline changes,
  JSON payloads, and CLI output without overwriting either setup.

## Honest effectiveness snapshot

All four surfaces are active focus areas with a committed target of **≥9/10**.
Ordered paths are below; see also `docs/application maturity.md`.

| Track | Current | Target | Remaining gap |
|-------|---------|--------|---------------|
| End-to-end "upload -> printable aligners" | ~9.0/10 for reviewed real geometry | ≥9/10 | Robust Open3D distance-offset validation and full-arch fixtures are in place; material/fit modeling remains out of scope. |
| Surface-scan staging + honest review aid | ~8.7/10 | ≥9/10 | Learned-vs-heuristic benchmarking and real-scan smoke coverage are in place; production learned weights and broader labelled real-case benchmarks remain optional/offline expansion. |
| CBCT root/bone-aware planning from a raw volume | ~8.4/10 | ≥9/10 | Phase 12 is complete as a safety-gated proposal workflow; caller-supplied sparse masks, limited open-volume validation, and no bundled clinical-grade segmenter hold back broader maturity. |
| In-app AI assistant (chat) | ~8.5/10 | ≥9/10 | SSE streaming and provider/model UX are in place; richer provider-native stream adapters and tool-style plan actions remain. |

## Remaining roadmap

### Order Of Operations To ≥9/10

This is the single recommended execution sequence. Phases are grouped into waves
by dependency; within a wave, items can run in parallel. A 10/10 is intentionally
NOT a target for the geometry tracks (no material/fit/physical-use modeling).

**Completed**

1. **Phase 9.1** (Track 1): spatial-grid shell QA for pure-Python shell builds.
2. **Phase 15 partial** (Track 4): normal chat flow + Cursor-style provider/model
   selection.
3. **Phase 13** (Track 2): benchmark corpus metadata, metric deltas, and messy
   shell/collision tracking.
4. **Phase 16** (Track 2): full triangle-level collision/IPR, including automatic
   reviewed mesh extraction from the local workspace with sampled/bbox fallback.
5. **Phase 15 remainder** (Track 4): SSE chat streaming path with JSON fallback.
6. **Prereq** (Track 1/3): Open3D in a test/CI environment.
7. **Phase 9.2 + 9.3** (Track 1): Open3D distance-field offset correction in the
   robust backend, validated vs pure-Python QA on a messy corpus.
8. **Phase 9.4** (Track 1): full-arch known-good fixtures from an independent mesh
   generator with hash/metric comparison.
9. **Phase 14** (Track 2): mature + benchmark the learned ONNX segmentation vs the
   heuristic on the Phase 13/16 benchmark corpus. Core Track 2 ~7.8 -> ~9 move.
10. **Phase 12a -> 12b -> 12c** (Track 3): raw-volume root/bone proposals,
   auto-registration proposal path, then volume benchmarks + fail-closed tests.
   Each step keeps proposals untrusted until human review and fails closed without
   the extras.

**Remaining**

No original phase checklist items remain in this roadmap. Further maturity work is
validation, corpus, optional-backend, provider-adapter, audit/export hardening,
and the treatment-system parity layers below. The geometry tracks still
intentionally stop short of physical-use/material/fit guarantees.

1. **Phase 17** (Track 2/UI): setup comparison + live restaging workbench.
   Backend comparison/restage contracts, CLI output, and the browser Review-side
   compare panel are in place. Next, deepen this into a full side-by-side 3D
   workspace for current/generated/edited/saved-version setups, including
   per-stage visual diff controls and non-overwriting version promotion.
2. **Phase 18** (Track 2/planning): richer 3D controls and arch response.
   Expand direct controls for translation, intrusion/extrusion, rotation, crown
   tip, crown torque, arch-form expansion/contraction, attachment/cut metadata,
   IPR/spacing, tooth locking, and movement exclusions. Add visible same-arch
   response proposals that preserve contacts/spacing when possible, with
   provenance and review gates.
3. **Phase 19** (Track 2/data): longitudinal case-bundle benchmarks.
   Complete for the current corpus-readiness scope: manifests, CLI registration,
   validated sidecars, and benchmark coverage metrics exist for target setup,
   tracking error, and refinement-prediction readiness. Deeper numeric outcome
   errors can be added once consented before/after/refinement scan bundles exist.

### Recently Completed Reference

- [x] Phase 9.1-9.4: robust shell QA, optional Open3D distance-offset backend,
  mesh-processing CI lane, messy validation fixtures, and independent full-arch
  shell comparison metrics.
- [x] Phase 13 + 16: validation benchmark deltas, reviewed non-PHI corpus
  metadata, messy-shell metrics, and full triangle-level collision/IPR with
  workspace mesh extraction plus sampled/bbox fallback.
- [x] Phase 15: bounded chat memory, incremental rendering, Enter-to-send,
  provider/model split, connector model catalogs, custom model IDs, PHI-share
  gating, SSE streaming, and non-streaming fallback.

### Phase 14: Segmentation Maturity

- [x] Mature the optional learned ONNX segmentation backend to reduce manual
  review burden on crowded/contacting arches.
- [x] Benchmark learned vs. heuristic segmentation on the Phase 13/16 benchmark
  corpus while keeping the heuristic backend as the no-dependency fallback.

### Phase 12: Automated CBCT Root/Bone Segmentation + Auto-Registration

> The longest road by far. Each step keeps proposals untrusted until human review
> and fails closed without the optional extras.

- [x] **Phase 12a:** optional volume-processing path, behind optional extras, that
  proposes root surfaces/centerlines and alveolar bone boundaries from CBCT, fed
  into the reviewed-anatomy pipeline as `PROPOSED` only (human review still
  required before any proposal becomes trusted).
- [x] **Phase 12b:** promote the Open3D ICP registration experiment to an
  auto-registration proposal path with quality metrics and human acceptance gating.
- [x] **Phase 12c:** synthetic + reviewed open-volume benchmarks, plus end-to-end
  fail-closed tests proving raw-volume/extra absence and rejected anatomy never
  promote a plan to trusted root/bone-aware behavior.
