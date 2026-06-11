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

## Honest effectiveness snapshot

| Track | Current | Remaining gap |
|-------|---------|---------------|
| End-to-end "upload -> printable aligners" | ~7/10 for reviewed real geometry | Robust offset/booleans, harder mesh repair, messy fixture corpus, and material/fit modeling are still out of scope. |
| Surface-scan staging + honest review aid | ~7/10 | More real-scan labels and learned/stronger segmentation would reduce review burden. |
| CBCT root/bone-aware planning from a raw volume | ~1-2/10 | Raw-volume root/bone segmentation and auto-registration are still not implemented. |

## Remaining roadmap

### Phase 9 follow-up: robust shell backend

- [ ] Add optional `mesh-processing` backend for stronger repair/offset behavior
  (winding repair, robust normal handling, true Minkowski-style offset or boolean
  shell construction).
- [ ] Keep the current pure-Python shell path as the no-extra fallback.
- [ ] Add fixtures that compare the optional backend against the pure-Python
  shell QA report on messy but non-PHI meshes.
- [ ] Add full-arch known-good shell fixtures from an independent mesh pipeline
  and compare hashes/metrics against OpenSource Ortho exports.

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
