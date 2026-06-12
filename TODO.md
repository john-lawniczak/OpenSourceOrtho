# TODO

## Product goal

The browser workspace turns uploaded STL scans, and reviewed CBCT-derived anatomy
when present, into reproducible staged geometry and 3D-printable model/shell
artifacts. Safety posture is unchanged and fail-closed: generating geometry never
means diagnosis, clinical approval, treatment clearance, or that physical use is
safe. Printing, fit, materials, post-processing, and any physical use remain the
user's own responsibility and risk. Every output must keep its review tier,
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

## Honest effectiveness snapshot

All four surfaces are active focus areas with a committed target of **≥9/10**.
Ordered paths are below; see also `docs/application maturity.md`.

| Track | Current | Target | Remaining gap |
|-------|---------|--------|---------------|
| End-to-end "upload -> printable aligners" | ~8.5/10 for reviewed real geometry | ≥9/10 | Robust true offset/booleans, full-arch known-good fixtures from an independent pipeline, and material/fit modeling are still out of scope. |
| Surface-scan staging + honest review aid | ~7.8/10 | ≥9/10 | Reviewed full-geometry collision/IPR is wired from workspace assets; stronger learned segmentation and broader real-case benchmarks remain. |
| CBCT root/bone-aware planning from a raw volume | ~1-2/10 | ≥9/10 | Raw-volume root/bone segmentation and auto-registration are still not implemented. Longest road by far. |
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

**Next Wave — optional mesh extra (Open3D), enabled once then reused**

6. **Prereq:** stand up Open3D in a test/CI environment (shared by 9.2/9.3
   and 12b).
7. **Phase 9.2 + 9.3** (Track 1): true boolean/SDF offset in the robust backend,
   then validate it vs the pure-Python QA on a messy corpus. The real Track 1
   ~8 -> ~9 move.
8. **Phase 9.4** (Track 1): full-arch known-good fixtures from an independent mesh
   pipeline. Completes Track 1.

**Then — Track 2 completion**

9. **Phase 14** (Track 2): mature + benchmark the learned ONNX segmentation vs the
   heuristic on the Wave 1 corpus. Core Track 2 ~7 -> ~9 move.

**Long-running Track 3**

10. **Phase 12a -> 12b -> 12c** (Track 3): raw-volume root/bone proposals,
   auto-registration proposal path, then volume benchmarks + fail-closed tests.
   Each step keeps proposals untrusted until human review and fails closed without
   the extras.

### Phase 15 Remainder: AI Chat Streaming

- [x] Stream assistant tokens when the provider supports it (Server-Sent Events or
  chunked fetch), with a graceful non-streaming fallback for providers/local that
  do not.

### Phase 9 Follow-Up: Robust Shell Backend 9.2-9.4

- [x] Phase 9 (done): backend selection (`shell_backend`), optional
  `mesh-processing` (Open3D) repair path (`aligner_shell_robust.py`), fail-closed
  fallback to pure-Python with the downgrade recorded in manifest/API/UI, and
  shared `assemble_shell` so QA is identical across backends. See
  `docs/aligner-shell-backend.md`.
- [x] Phase 9 (done): keep the current pure-Python shell path as the no-extra
  fallback.
- [ ] **Prereq:** stand up Open3D in a test/CI environment (shared with Phase 9
  and Phase 12b).
- [ ] **Phase 9.2:** implement a true Minkowski-style offset or boolean shell
  construction in the robust path (currently mesh repair + normal offset only).
- [ ] **Phase 9.3:** validate the robust backend vs the pure-Python shell QA on
  messy but non-PHI meshes (this validation is what moves Track 1 from ~8 toward 9).
- [ ] **Phase 9.4:** add full-arch known-good shell fixtures from an independent
  mesh pipeline and compare hashes/metrics against OpenSource Ortho exports.

### Phase 16 Remainder: Full-Geometry Collision/IPR

- [x] Add full triangle-level proximity/distance when reviewed geometry is supplied
  in memory.
- [x] Keep the current bbox-prefilter + sampled-point path as the no-dependency
  fallback, and keep the bbox fallback when samples are absent.
- [x] Add fixtures comparing sampled vs full-triangle contact distances so the
  precision/recall improvement is measurable.
- [x] Wire automatic full-triangle extraction from reviewed mesh assets/workspace
  into the collision rule without serializing full scan geometry into plan JSON.

### Phase 14: Segmentation Maturity

- [ ] Mature the optional learned ONNX segmentation backend to reduce manual
  review burden on crowded/contacting arches.
- [ ] Benchmark learned vs. heuristic segmentation on the Phase 13 fixtures while
  keeping the heuristic backend as the no-dependency fallback.

### Phase 12: Automated CBCT Root/Bone Segmentation + Auto-Registration

> The longest road by far. Each step keeps proposals untrusted until human review
> and fails closed without the optional extras.

- [ ] **Phase 12a:** optional volume-processing path, behind optional extras, that
  proposes root surfaces/centerlines and alveolar bone boundaries from CBCT, fed
  into the reviewed-anatomy pipeline as `PROPOSED` only (human review still
  required before any proposal becomes trusted).
- [ ] **Phase 12b:** promote the Open3D ICP registration experiment to an
  auto-registration proposal path with quality metrics and human acceptance gating.
- [ ] **Phase 12c:** synthetic + reviewed open-volume benchmarks, plus end-to-end
  fail-closed tests proving raw-volume/extra absence and rejected anatomy never
  promote a plan to trusted root/bone-aware behavior.
