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
- Real triangle-triangle self-intersection engine (Möller narrow phase behind an
  spatial-grid broad phase) and nonmanifold-edge detection replacing the
  box-overlap approximation, per-artifact `failed_checks` explanations, and an
  independent analytic known-good oracle (closed-form slab volume) plus synthetic
  messy fixtures.
- In-app AI assistant now has bounded conversation memory, incremental message
  rendering, Enter-to-send, provider/model split with per-provider model memory,
  connector model catalogs, custom self-hosted model IDs, and per-request
  credential/PHI-share gating. True token streaming is still pending.
- Benchmark reports now include metric deltas, reviewed non-PHI corpus metadata
  for the bundled Sample Test Case, messy-shell metrics, and sampled-vs-triangle
  collision/IPR distance metrics.

## Honest effectiveness snapshot

All four surfaces are active focus areas with a committed target of **≥9/10**.
Ordered paths are below; see also `docs/application maturity.md`.

| Track | Current | Target | Remaining gap |
|-------|---------|--------|---------------|
| End-to-end "upload -> printable aligners" | ~8.5/10 for reviewed real geometry | ≥9/10 | Robust true offset/booleans, full-arch known-good fixtures from an independent pipeline, and material/fit modeling are still out of scope. |
| Surface-scan staging + honest review aid | ~7.5/10 | ≥9/10 | Triangle-level collision/IPR now has an in-memory geometry path, but automatic full-geometry extraction and stronger learned segmentation remain. |
| CBCT root/bone-aware planning from a raw volume | ~1-2/10 | ≥9/10 | Raw-volume root/bone segmentation and auto-registration are still not implemented. Longest road by far. |
| In-app AI assistant (chat) | ~8/10 | ≥9/10 | True token streaming and richer provider adapters remain; the normal conversation flow and provider/model UX are now in place. |

## Remaining roadmap

### Order of operations to ≥9/10 (all four tracks)

This is the single recommended execution sequence. Phases are grouped into waves
by dependency; within a wave, items can run in parallel. A 10/10 is intentionally
NOT a target for the geometry tracks (no material/fit/physical-use modeling).
Detailed task lists for each phase follow, in this same order.

**Done waves**

1. **Phase 9.1** (Track 1): spatial-grid shell QA for pure-Python shell builds.
2. **Phase 15 partial** (Track 4): normal chat flow + Cursor-style provider/model
   selection. True token streaming remains.
3. **Phase 13** (Track 2): benchmark corpus metadata, metric deltas, and messy
   shell/collision tracking.

**Wave 2 — optional mesh extra (Open3D), enabled once then reused**

4. **Prereq:** stand up Open3D in a test/CI environment (shared by 9.2/9.3, 16,
   and 12b).
5. **Phase 9.2 + 9.3** (Track 1): true boolean/SDF offset in the robust backend,
   then validate it vs the pure-Python QA on a messy corpus. The real Track 1
   ~8 -> ~9 move.
6. **Phase 16 remaining** (Track 2): automatic full-geometry collision/IPR from
   reviewed mesh assets. The in-memory triangle path and sampled fallback now
   exist.
7. **Phase 9.4** (Track 1): full-arch known-good fixtures from an independent mesh
   pipeline. Completes Track 1.

**Wave 3 — Track 2 completion**

8. **Phase 14** (Track 2): mature + benchmark the learned ONNX segmentation vs the
   heuristic on the Wave 1 corpus. Core Track 2 ~7 -> ~9 move.

**Wave 4 — Track 3 (longest road; run as a parallel long-running track)**

9. **Phase 12a -> 12b -> 12c** (Track 3): raw-volume root/bone proposals,
   auto-registration proposal path, then volume benchmarks + fail-closed tests.
   Each step keeps proposals untrusted until human review and fails closed without
   the extras.

---

### Phase 9.1 (Wave 0, PRIORITY): scale the pure-Python shell QA before real arch use

> **Why this gates real multi-tooth use:** the real triangle-triangle
> self-intersection engine and the `min_inner_outer_clearance` check are both
> O(n^2) and run on **every** pure-Python shell build. Measured cost already hits
> ~16.7s at ~8,460 shell triangles; a real full-arch reviewed shell is far larger,
> so per-stage builds would take minutes and hang the print path. The optional
> robust (Open3D) backend handles intersection internally, but the **pure-Python
> fallback is the always-on default**, so this must land before the shell QA runs
> on real multi-tooth reviewed plans.

- [x] Replace the O(n^2) self-intersection broad phase with a uniform spatial-grid
  (hash-bucket) broad phase so only triangles in neighboring cells reach the exact
  Möller narrow phase; target ~linear scaling on clean meshes.
- [x] Replace the O(V^2) `min_inner_outer_clearance` scan with a spatial-grid /
  nearest-neighbor query over inner vs outer vertices.
- [x] Add a performance regression test (full-arch-scale synthetic shell, assert
  build completes under a fixed wall-clock budget) so the O(n^2) cost cannot
  silently return.
- [x] Keep results identical to the current exact engine on the existing fixtures
  (the grid changes only which pairs are tested, not the intersection test).

### Phase 15 (Wave 1): AI chat UX + provider/model selection (Track 4)

> **Current state:** the assistant now behaves like a normal bounded
> conversation, with provider/model selection and per-request credential handling.
> The remaining chat gap is true provider token streaming.

#### Goal A: make the chat flow like a normal conversation

- [x] Thread conversation history: send prior turns to the backend (bounded /
  truncated) and accept multi-turn input in `answer_chat_payload` / `ChatRequest`
  so the assistant has memory across turns.
- [x] Render messages incrementally (append, do not rebuild `innerHTML` each
  render); preserve scroll position and auto-scroll to the latest message; keep
  input focus after sending.
- [x] Add a live pending/typing indicator and Enter-to-send / Shift+Enter for a
  newline; disable the composer only while a turn is in flight, not the whole panel.
- [ ] Stream assistant tokens when the provider supports it (Server-Sent Events or
  chunked fetch), with a graceful non-streaming fallback for providers/local that
  do not.

#### Goal B: Cursor-style provider + model selection

- [x] Split the single dropdown into two steps: pick the provider, then pick a
  model from that provider's model list (remember the last selection per provider).
- [x] Give each connector in `connector_catalog()` a real list of selectable
  models instead of a single "configured externally" string; optionally allow a
  free-text model id for self-hosted/open-source endpoints.
- [x] Show per-provider affordances inline: which need an API key, which share
  patient data, and the local helper as the default no-key on-device option.

#### Safety constraints (unchanged - must hold)

- [x] Keep model output separated from deterministic findings; any model-generated
  finding still passes `lint_finding()` before display or export.
- [x] Preserve per-request credential handling (API keys read at send time, never
  stored/persisted) and the PHI-share acknowledgement + `shares_patient_data`
  labeling before any non-local provider receives plan context.

### Phase 13 (Wave 1): broader benchmark corpus (Track 2)

- [x] Add reviewed non-PHI benchmark corpus metadata beside the current synthetic
  fixtures. Current implementation uses the bundled Sample Test Case manifest;
  true third-party open-dataset cases remain a future expansion.
- [x] Track benchmark reports over time so segmentation, movement, collision/IPR,
  and shell changes show metric deltas instead of only pass/fail status.
- [x] Add optional benchmark fixtures for messy shell geometry once the robust
  shell backend exists.

### Phase 9 follow-up (Wave 2): robust shell backend 9.2 - 9.4 (Track 1)

- [x] Phase 9 (done): backend selection (`shell_backend`), optional
  `mesh-processing` (Open3D) repair path (`aligner_shell_robust.py`), fail-closed
  fallback to pure-Python with the downgrade recorded in manifest/API/UI, and
  shared `assemble_shell` so QA is identical across backends. See
  `docs/aligner-shell-backend.md`.
- [x] Phase 9 (done): keep the current pure-Python shell path as the no-extra
  fallback.
- [ ] **Prereq:** stand up Open3D in a test/CI environment (shared with Phase 16
  and Phase 12b).
- [ ] **Phase 9.2:** implement a true Minkowski-style offset or boolean shell
  construction in the robust path (currently mesh repair + normal offset only).
- [ ] **Phase 9.3:** validate the robust backend vs the pure-Python shell QA on
  messy but non-PHI meshes (this validation is what moves Track 1 from ~8 toward 9).
- [ ] **Phase 9.4:** add full-arch known-good shell fixtures from an independent
  mesh pipeline and compare hashes/metrics against OpenSource Ortho exports.

### Phase 16 (Wave 2): full triangle-level collision/IPR (Track 2)

- [x] Add full triangle-level proximity/distance when reviewed geometry is supplied
  in memory; automatic extraction from mesh assets remains pending.
- [x] Keep the current bbox-prefilter + sampled-point path as the no-dependency
  fallback, and keep the bbox fallback when samples are absent.
- [x] Add fixtures comparing sampled vs full-triangle contact distances so the
  precision/recall improvement is measurable.
- [ ] Wire automatic full-triangle extraction from reviewed mesh assets/workspace
  into the collision rule without serializing full scan geometry into plan JSON.

### Phase 14 (Wave 3): segmentation maturity (Track 2)

- [ ] Mature the optional learned ONNX segmentation backend to reduce manual
  review burden on crowded/contacting arches.
- [ ] Benchmark learned vs. heuristic segmentation on the Phase 13 fixtures while
  keeping the heuristic backend as the no-dependency fallback.

### Phase 12 (Wave 4): automated CBCT root/bone segmentation + auto-registration (Track 3)

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
