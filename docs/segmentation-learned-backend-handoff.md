# Handoff prompt — learned tooth-segmentation backend

> Paste the block below into a fresh chat to continue this work with clean
> context. It is self-contained; the new session should read the linked files
> rather than rely on prior conversation.

---

```text
You are continuing work on OpenSource Ortho, an open, safety-boundary-first
clear-aligner treatment-PLANNING research toolkit. It is NOT a medical device,
NOT a diagnosis tool, and NOT an autonomous treatment planner. Never describe it
as such. Segmentation only PROPOSES per-tooth regions for human review; it is
never a diagnosis or a statement that treatment is needed, possible, safe, or
complete. Read CLAUDE.md and docs/MAINTAINABILITY.md before changing code.

## Your task
Implement Phase 1 of the learned tooth-segmentation backend described in
docs/segmentation-learned-backend.md. Read that doc first — it is the spec.

Goal of this phase: add a learned segmenter that DROPS INTO the existing
contract, behind an install/weights check, with the heuristic as the always-on
fallback. It must be testable BEFORE any model weights exist (a graceful
"weights absent -> fall back to heuristic" path), so this phase ships value and
tests without committing any model or dataset.

## Repo / environment
- Repo: github.com/john-lawniczak/OpenSourceOrtho ; working branch: feat/v1.2.
- Start clean: `git switch feat/v1.2 && git pull`. Make changes on this branch
  (or a feat/ branch off it) and commit with type-tagged subjects
  (Add:/Fix:/Perf:/Tweak:/Test:/Refactor:/docs:).
- Test commands (keep ALL green before committing):
  - `python3 -m pytest -q`            (currently 320 passed, 1 skipped)
  - `python3 tools/check_maintainability.py --strict`   (pre-commit hook runs it)
  - `cd ui && node --test`            (47 tests)
- Maintainability caps enforced by --strict: Python file <= 300 lines, function
  <= 60 lines, class <= 150. Split into a focused module rather than trimming
  good docs. JS files are NOT line-capped by the tool.
- Local workflow (docs/CLAUDE.local.md, gitignored): append a dated entry to
  docs/Dev_history.md (gitignored) on behavior changes; update
  docs/OpenAI_Agents.md ONLY if model-PROVIDER behavior changes (a local ONNX
  model is not a provider, so likely N/A). Push when asked.

## The contract you must preserve (drop-in; do not change downstream)
- `orthoplan/segmentation/heuristic.py`: `ToothSegment` dataclass
  (tooth_value, triangles, centroid, confidence) and `default_arch_order(arch)`.
- `orthoplan/segmentation/auto.py`: `load_local_segmenter()` selects the active
  backend; `tooth_values_for_arch(arch, missing_teeth)` gives canonical FDI order.
  The active segmenter exposes `.segment(vertices, *, arch, tooth_values=None)`
  returning `list[ToothSegment]`, plus `.name`, `.version`, `.backend`.
- Downstream is already wired and must NOT need changes:
  `segmentation_api.segment_payload` -> `mesh_export.write_segment_meshes` ->
  `api.evaluate_*` returns `render_meshes` with `source: "model-generated"` ->
  ui/render.js routes those to `viewer3d.js` `loadToothFragments` (fragment mode
  renders real per-tooth crowns at true scan positions, moving by the plan).

## Current state (so you don't re-derive it)
- The shipped segmenter is the dependency-free heuristic (hybrid arch graph-cut):
  `segmentation/{heuristic,hybrid,arch_profile}.py`. Recent accuracy work:
  - `arch_profile.place_cuts()` places cuts at the most prominent valleys/peaks
    with a minimum separation (fixed a sliver/label-shift bug; synthetic
    label-accuracy 0.63 -> 0.93). Used by find_boundaries + hybrid.
  - `heuristic._COUNT_SEPARATION_FRACTION = 0.35` (was 0.5) — recovered real-scan
    crown counts to 14/14 on both bundled arches.
- The heuristic produces ROUGH per-tooth meshes: each cut is a planar-ish slice
  of the whole shell (crown + gum), so separated crowns look "shattered" in the
  viewer's Planned view. THIS is the quality ceiling the learned backend fixes —
  not a placement bug. The viewer fragment mode and arrow indicators already work.

## Measurement gates (prove the model is better, don't just swap it)
- `orthoplan/validation/synthetic_arch.py` builds arches with known per-triangle
  truth, incl. realism knobs: `realistic_widths` (uneven crowns), `occlusal_flat`
  (flat molar plateaus), `noise`. `segmentation_truth.score_segmentation` scores
  region_purity + triangle_label_accuracy.
- Gated cases in `orthoplan/validation/segmentation_cases.py` (run via
  `orthoplan.validation.run_measurement_lab(...)`): segmentation-full-arch-accuracy
  (floors purity 0.88 / label 0.85), -realistic-arch-accuracy (0.85/0.85),
  -missing-tooth, -open-gap.
- `tests/test_segmentation_real_scan.py`: bundled real scans
  (ui/example-scans/canonical-orthocad-001/*.stl) must keep 14/14 crowns + time
  budget. A learned backend must MEET OR BEAT every floor.
- ADD in this phase a crown-compactness / boundary-smoothness metric + case so
  the "rough wedge" failure mode is measurable (the synthetic arch can't fully
  express it; note the need for a small labelled real-scan fixture later).

## Constraints (hard)
- Core install stays light + offline. The learned backend is an OPTIONAL extra
  (e.g. `pip install ".[ml-seg]"`) pulling onnxruntime + numpy only — NEVER torch
  at runtime. Training tooling lives outside the shipped package.
- Do NOT commit model weights or datasets (size + license/provenance). Resolve
  weights from a path/env var/cache; if absent, fall back to the heuristic and
  record the backend name. On-device only (scan bytes never leave the machine).
- Keep the heuristic as the default fallback; never make the core depend on the
  optional extra.

## Phase 1 deliverable (definition of done)
1. `orthoplan/segmentation/learned.py`: a segmenter implementing
   `.segment(vertices, *, arch, tooth_values=None) -> list[ToothSegment]` via
   onnxruntime, with FDI labeling through `tooth_values_for_arch`. If
   onnxruntime or weights are unavailable, it must be inert (raise a clear
   "unavailable" signal the loader catches).
2. `load_local_segmenter()` registers the learned backend behind an
   install/weights capability check and falls back to the heuristic; backend name
   surfaces in `_segmenter_metadata` / segment_payload.
3. `pyproject.toml`: optional `ml-seg` extra (onnxruntime, numpy). No torch.
4. Tests: loader prefers learned when available and falls back cleanly when not
   (mock/skip without weights); the new compactness metric + case; ALL existing
   floors stay green. pytest + node --test + maintainability --strict all pass.
5. Update docs/segmentation-learned-backend.md status and check off the
   integration checklist items you complete.

Do NOT attempt to train or bundle a model in this phase. Build the contract,
the fallback, the packaging, and the measurement.

## Model availability (checked June 2026 — do not re-litigate)
There is NO turnkey ONNX tooth-segmenter to drop in. MeshSegNet
(github.com/Tai-Hsien/MeshSegNet) has MIT-licensed CODE and ships pretrained
PyTorch weights (upper + lower), but: (a) no ONNX export is provided — it is
PyTorch only, and export is fiddly because its GLM layers take mesh adjacency
matrices as inputs; (b) the WEIGHTS' license is undocumented (trained on a
private clinical dataset — clear terms before redistributing); (c) it needs real
per-cell preprocessing (decimate to <=10k cells, 15-dim features, per arch, 15
classes -> FDI). Teeth3DS+/3DTeethSeg'22 data is CC BY-NC-ND 4.0 (non-commercial,
no derivatives) — do NOT train the shipped backend on it.

So Phase 1 assumes NO weights and NO torch at runtime, and is fully testable
without a model. Exporting MeshSegNet -> ONNX and clearing its weights' license
is a SEPARATE later spike (see docs/segmentation-learned-backend.md "Model
availability" + "Candidate approaches"). Resolve weights from a user-supplied
path so the project never commits or redistributes them.

A real OrthoCAD export for manual spot-checks lives locally at
~/Desktop/OrthoCAD_Export_John K/ (whole-arch shells; PHI — never commit it).
```
