# TODO

## Product goal

The browser workspace turns uploaded STL (and, when reviewed, CBCT) scans into
reproducible **staged geometry AND 3D-printable aligner-shell models** the user
can print locally. Safety posture is unchanged and fail-closed: generating
printable geometry never means diagnosis, clinical approval, treatment clearance,
or that physical use is safe. Printing, fit, materials, and any physical use
remain the user's own responsibility and risk, and every output keeps its review
tier and unresolved data gaps clearly labeled.

## Completed (v1.2)

Phases 1-8 (full history in git):

- Durable STL/CBCT intake, case storage, provenance, and review tiers
  (STL-only → enhanced-records → CBCT-attached → root/bone-aware).
- STL surface planning: scale-gated mm checks, auto-segmentation + review UI,
  per-tooth fragment rendering, shared-engine checks, surface-gap reports.
- Real per-tooth print/export with scan/fragment/findings/frame hashes and tier
  labels (real vertices for reviewed segmentation, labeled proxy fallback).
- Local DICOM metadata intake (PHI-stripped, no volume bytes) + 3D Slicer handoff.
- STL↔CBCT registration model with fail-closed acceptance gating.
- Reviewed CBCT-derived anatomy (roots, axes, bone) with accept/correct/reject UI.
- Root/bone-aware review checks (proximity, cortical, context, cannot-assess).
- Browser↔mobile case-review handoff (opaque, edit-locked, link/QR/deep-link).

## Effectiveness roadmap — drive every track to ≥ 7/10

Honest self-assessment of the current build:

| Track | Now | Target |
|-------|-----|--------|
| End-to-end "upload → printable aligners" | ~2/10 (manufacturing half missing) | ≥ 7/10 |
| Surface-scan staging + honest review aid | ~6-7/10 | ≥ 7/10 (hold + sharpen) |
| CBCT root/bone-aware planning from a raw volume | ~1-2/10 | ≥ 7/10 |

### Phase 9: Aligner-shell generation — the manufacturing step (track 1)

> Single biggest gap between "staging tool" and "aligner generator".

- [x] Build a per-stage aligner-shell mesh by offsetting the reviewed stage
  surface outward along vertex normals by a configurable sheet thickness
  (default ~0.5-0.75 mm).
- [x] Close the shell into a watertight, manifold printable solid (outer offset
  surface + inner cavity surface + stitched rim at open boundaries).
- [x] Generate a gingival trim: cut the shell along a margin plane derived from
  trusted tooth axes (fail-closed: no trim when the occlusal axis is unknown).
- [x] Add aligner-shell export settings (sheet thickness, trim margin, enable
  flag) and emit shell STLs in the print package, labeled shell-vs-model, with
  thickness + trim parameters and the shell hash in the manifest.
- [x] Always-available pure-Python shell path; fail closed (model only, no shell)
  when geometry is missing or unreviewed.
- [ ] Robust offset/booleans behind the optional `mesh-processing` extra
  (winding repair, true Minkowski offset) — future enhancement over the
  vertex-normal approximation.
- [x] Tests: shell is watertight (every edge shared by 2 faces), measured
  thickness is within tolerance of the request, trim removes sub-gingival
  geometry, and export falls closed without reviewed geometry.
- [x] Manufacturing-readiness QA for the pure-Python shell path: weld/drop
  degenerate input triangles, report watertightness, connected components,
  thickness distribution, shell hashes, and fail-closed model-only reasons in
  the package manifest/API.

### Phase 10: Real mesh collision + interproximal contact (track 2)

- [x] Replace axis-aligned bounding-box-only overlap with capped representative
  surface-sample proximity between adjacent crown meshes.
- [x] Detect true interproximal contact and quantify the IPR (mm of enamel)
  needed to resolve it.
- [x] Keep the BBox test as a fast pre-filter; escalate to sample distance only
  on candidate overlap.
- [x] Fail closed to the BBox check with a labeled note when representative
  samples are unavailable.
- [x] Fixture tests with known-overlapping and known-clear crown pairs.

### Phase 11: Root-aware / biomechanical movement (tracks 2 & 3)

- [x] When trusted root anatomy exists, move teeth about the root-derived center
  of resistance instead of the crown centroid.
- [x] Render tip/torque as true rotations about the root-based long axis.
- [x] Fail closed to the current crown-centroid visualization (kept labeled
  "visualization assumption, not biomechanics") when roots are unavailable.
- [x] Tests: with roots, the apex moves opposite the crown under tipping; without
  roots, movement output is unchanged.

### Phase 12: Automated CBCT root/bone segmentation + auto-registration (track 3)

- [ ] Add an optional volume-processing path (behind the dicom/mesh extras) that
  proposes root surfaces/centerlines and an alveolar bone boundary from the CBCT.
- [ ] Feed proposals into the existing reviewed-anatomy pipeline as PROPOSED
  only — never auto-trusted; human review still required.
- [ ] Promote the Open3D ICP registration experiment to a default auto-
  registration step with a quality gate (still requires human acceptance).
- [ ] Tests on synthetic/fixture volumes: proposals carry provenance + confidence,
  stay untrusted until accepted, and fail closed without the extras.

### Phase 13: Measured accuracy / validation benchmarks (quantifies all tracks)

- [x] Add ground-truth fixture cases (synthetic + any reviewed open datasets) for
  segmentation, movement, collision, and shell thickness.
- [x] Add a benchmark harness reporting per-component metrics (Dice/IoU for
  segmentation, mm error for movement/shell, precision/recall for collision).
- [x] Surface the metrics as tracked numbers (reported, not pass/fail gates at
  first) so "accuracy" stops being unmeasured.

### Phase 14: Segmentation maturity — learned model (track 2)

- [ ] Mature the optional learned ONNX segmentation backend to cut the manual-
  review burden on crowded/contacting arches.
- [ ] Benchmark learned vs. heuristic on the Phase 13 fixtures; keep the
  heuristic as the no-dependency fallback.
