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
  cleanup, watertightness, connected components, rim closure, approximate
  self-intersection signals, inner/outer clearance, thickness distribution,
  printer tolerance metadata, and `CONSISTENT` / `ISSUES` / `NOT_APPLICABLE`
  verdicts in API/export manifests.
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
  AABB broad phase) and nonmanifold-edge detection replacing the box-overlap
  approximation, per-artifact `failed_checks` explanations, and an independent
  analytic known-good oracle (closed-form slab volume) plus synthetic messy
  fixtures.

## Honest effectiveness snapshot

| Track | Current | Remaining gap |
|-------|---------|---------------|
| End-to-end "upload -> printable aligners" | ~8/10 for reviewed real geometry | Robust offset/booleans and harder mesh repair, a full-arch known-good/messy real-scan corpus, and material/fit modeling are still out of scope. |
| Surface-scan staging + honest review aid | ~7/10 | More real-scan labels and learned/stronger segmentation would reduce review burden. |
| CBCT root/bone-aware planning from a raw volume | ~1-2/10 | Raw-volume root/bone segmentation and auto-registration are still not implemented. |

## Remaining roadmap

### Path to Track 1 ~9/10 (ordered)

Track 1 is ~8/10 today. The ordered work to reach ~9/10, gated by the safety
posture (no material/fit/physical-use claims) and the pure-Python-always-on rule:

1. **Phase 9.1 (PRIORITY, do first):** make the pure-Python shell QA scale to
   real arches (spatial-grid broad phase). Blocks real multi-tooth use today.
2. **Phase 9.2:** implement a true boolean/signed-distance (Minkowski) offset in
   the robust backend, replacing the repair-only normal offset.
3. **Phase 9.3:** install Open3D in a test environment and validate the robust
   backend vs the pure-Python QA on a synthetic messy corpus. This validation is
   the actual ~8 -> ~9 move; without it the robust offset is unproven.
4. **Phase 9.4:** add full-arch known-good shell fixtures from an independent mesh
   pipeline and compare hashes/metrics against OpenSource Ortho exports.

A 10/10 is intentionally NOT on this path: it would require material deformation,
thermoforming fit, printer calibration, and physical validation, which this
safety-boundary-first toolkit deliberately does not model.

### Phase 9.1 (PRIORITY): scale the pure-Python shell QA before real arch use

> **Why this is a priority and gates real multi-tooth use:** the real
> triangle-triangle self-intersection engine and the `min_inner_outer_clearance`
> check are both O(n^2) and run on **every** pure-Python shell build. Measured
> cost already hits ~16.7s at ~8,460 shell triangles; a real full-arch reviewed
> shell is far larger, so per-stage builds would take minutes and effectively
> hang the print path. The optional robust (Open3D) backend handles intersection
> internally, but the **pure-Python fallback is the always-on default**, so this
> must be fixed before the shell QA is run on real multi-tooth reviewed plans.

- [ ] Replace the O(n^2) self-intersection broad phase with a uniform spatial-grid
  (hash-bucket) broad phase so only triangles in neighboring cells reach the exact
  Möller narrow phase; target ~linear scaling on clean meshes.
- [ ] Replace the O(V^2) `min_inner_outer_clearance` scan with a spatial-grid /
  nearest-neighbor query over inner vs outer vertices.
- [ ] Add a performance regression test (full-arch-scale synthetic shell, assert
  build completes under a fixed wall-clock budget) so the O(n^2) cost cannot
  silently return.
- [ ] Keep results identical to the current exact engine on the existing fixtures
  (the grid changes only which pairs are tested, not the intersection test).

### Phase 9 follow-up: robust shell backend (9.2 - 9.4)

- [x] Phase 9 (done): backend selection (`shell_backend`), optional
  `mesh-processing` (Open3D) repair path (`aligner_shell_robust.py`), fail-closed
  fallback to pure-Python with the downgrade recorded in manifest/API/UI, and
  shared `assemble_shell` so QA is identical across backends. See
  `docs/aligner-shell-backend.md`.
- [x] Phase 9 (done): keep the current pure-Python shell path as the no-extra
  fallback.
- [ ] **Phase 9.2:** implement a true Minkowski-style offset or boolean shell
  construction in the robust path (currently mesh repair + normal offset only).
- [ ] **Phase 9.3:** install Open3D in a test environment and add fixtures that
  compare the robust backend against the pure-Python shell QA report on messy but
  non-PHI meshes (this validation is what moves Track 1 from ~8 toward 9).
- [ ] **Phase 9.4:** add full-arch known-good shell fixtures from an independent
  mesh pipeline and compare hashes/metrics against OpenSource Ortho exports.

### Phase 12: automated CBCT root/bone segmentation + auto-registration

- [ ] Add an optional volume-processing path, behind optional extras, that
  proposes root surfaces/centerlines and alveolar bone boundaries from CBCT.
- [ ] Feed proposals into the existing reviewed-anatomy pipeline as `PROPOSED`
  only. Human review must still be required before any proposal becomes trusted.
- [ ] Promote the Open3D ICP registration experiment to an auto-registration
  proposal path with quality metrics and human acceptance gating.
- [ ] Add synthetic/fixture volume tests proving proposals carry provenance and
  confidence, stay untrusted until accepted, and fail closed without extras.

### Phase 13 follow-up: broader benchmark corpus

- [ ] Add reviewed open-dataset benchmark cases beside the current synthetic
  fixtures, with provenance and no PHI.
- [ ] Track benchmark reports over time so segmentation, movement, collision/IPR,
  and shell changes show metric deltas instead of only pass/fail status.
- [ ] Add optional benchmark fixtures for messy shell geometry once the robust
  shell backend exists.

### Phase 14: segmentation maturity

- [ ] Mature the optional learned ONNX segmentation backend to reduce manual
  review burden on crowded/contacting arches.
- [ ] Benchmark learned vs. heuristic segmentation on the Phase 13 fixtures while
  keeping the heuristic backend as the no-dependency fallback.

### Phase 15: AI chat UX + provider/model selection

> **Current state (clunky, needs rework):** the in-app assistant
> (`ui/app.js` send flow, `ui/render.js` `renderChat`, `orthoplan/ai_chat.py`,
> `orthoplan/ai_connectors.py`) does not behave like a normal chat:
> - **Single-turn, no memory.** Each "Ask AI" sends only the current message;
>   `answer_chat_payload` builds a session of just `[user, assistant]` and no prior
>   turns are passed back, so the assistant cannot reference earlier messages. A
>   real back-and-forth conversation is impossible today.
> - **No streaming.** The full answer appears at once after a static
>   "Reviewing the scoped plan context..." status; there is no token streaming or
>   live typing indicator.
> - **Coupled, hardcoded model picker.** One `<select id="chatModel">` carries both
>   provider and model via `data-provider` on a fixed option list; models are
>   "configured externally" with no per-provider model list or selection.
> - **Full re-render churn.** `renderChat` rebuilds `chatMessages.innerHTML` on
>   every render (including each keystroke), so scroll position jumps, focus is
>   fragile, and messages cannot append incrementally.

#### Goal A: make the chat flow like a normal conversation

- [ ] Thread conversation history: send prior turns to the backend (bounded /
  truncated) and accept multi-turn input in `answer_chat_payload` / `ChatRequest`
  so the assistant has memory across turns.
- [ ] Render messages incrementally (append, do not rebuild `innerHTML` each
  render); preserve scroll position and auto-scroll to the latest message; keep
  input focus after sending.
- [ ] Add a live pending/typing indicator and Enter-to-send / Shift+Enter for a
  newline; disable the composer only while a turn is in flight, not the whole panel.
- [ ] Stream assistant tokens when the provider supports it (Server-Sent Events or
  chunked fetch), with a graceful non-streaming fallback for providers/local that
  do not.

#### Goal B: Cursor-style provider + model selection

- [ ] Split the single dropdown into two steps: pick the provider, then pick a
  model from that provider's model list (remember the last selection per provider).
- [ ] Give each connector in `connector_catalog()` a real list of selectable
  models instead of a single "configured externally" string; optionally allow a
  free-text model id for self-hosted/open-source endpoints.
- [ ] Show per-provider affordances inline: which need an API key, which share
  patient data, and the local helper as the default no-key on-device option.

#### Safety constraints (unchanged - must hold)

- [ ] Keep model output separated from deterministic findings; any model-generated
  finding still passes `lint_finding()` before display or export.
- [ ] Preserve per-request credential handling (API keys read at send time, never
  stored/persisted) and the PHI-share acknowledgement + `shares_patient_data`
  labeling before any non-local provider receives plan context.
