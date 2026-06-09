# Scope: learned tooth-segmentation backend

> Status: **proposal / not yet built.** Educational tooling only — segmentation
> proposes per-tooth regions for review; it is never a diagnosis, a treatment
> decision, or a statement that care is needed, possible, safe, or complete.

## Why

The current segmenter (`orthoplan/segmentation/{heuristic,hybrid,arch_profile}.py`)
is a dependency-free 1-D valley/graph-cut heuristic. After recent fixes it gets
the **tooth count** and **boundary labels** right on the bundled real scans
(14/14 per arch), but the per-tooth meshes are **rough vertical wedge slabs**:
each cut is a planar-ish slice of the whole shell (crown + gum), so when the 3-D
viewer separates them they look shattered (see the "broken teeth" report). The
heuristic is a good *floor*; it is not crown-accurate geometry.

A learned mesh-segmentation model produces clean, curved per-tooth boundaries
that follow the gingival margin and interproximal contacts — the geometry the
"real crowns move at true positions" feature (`viewer3d.js` fragment mode) needs
to look right.

## The contract to preserve

Everything already routes through one small contract, so the model is a drop-in:

- Input: a whole-arch vertex list + `arch` (+ optional user `tooth_values` /
  missing-teeth hints). Same signature as `load_local_segmenter().segment(...)`.
- Output: `list[ToothSegment]` (`segmentation/heuristic.py`) — `tooth_value`,
  `triangles`, `centroid`, `confidence`. Downstream (`segmentation_api`,
  `mesh_export`, `api.render_meshes`, the viewer) is unchanged.
- Selection: `load_local_segmenter()` (`segmentation/auto.py`) already picks the
  active backend. The learned model registers here behind a capability/install
  check; the heuristic stays the default fallback.

**Implication:** no API, payload, plan-model, or UI changes are required to swap
the algorithm. This doc is about the model + its packaging, not the wiring.

## Candidate approaches (in rough order of effort)

1. **MeshSegNet / iMeshSegNet (Teeth3DS-trained), ONNX-exported.**
   Point/face-based network for intraoral scans; mature, public datasets
   (Teeth3DS, 3DTeethSeg22 MICCAI challenge). Export to ONNX and run via
   `onnxruntime` (CPU) so there is **no torch runtime dependency** for users.
2. **A lighter PointNet++-style face classifier** trained on the same data —
   smaller weights, lower accuracy, simpler to ship.
3. **Geometry upgrade, no ML:** curvature/normal-based watershed on the mesh
   graph (needs the half-edge adjacency we do not currently build). Cleaner cuts
   than the 1-D heuristic without weights, but well short of a trained model.

Recommendation: **(1) ONNX MeshSegNet**, with the heuristic retained as the
always-available fallback.

## Dependency & packaging strategy (hard requirement)

The core install must stay light and offline (see `CLAUDE.md` / maintainability
rules). So:

- The learned backend is an **optional extra** (e.g. `pip install
  ".[ml-seg]"`), pulling `onnxruntime` + `numpy` only — **never torch** at
  runtime. Training tooling lives outside the shipped package.
- Weights are **not committed** to the repo (size + provenance). Resolve from a
  local path / env var / cached download; if absent, `load_local_segmenter()`
  silently falls back to the heuristic and records the backend name (already
  surfaced in `segment_payload` metadata).
- On-device only: inference runs locally, same privacy posture as today (scan
  bytes never leave the machine; server resolves server-local scans only).

## Data & licensing

- Teeth3DS / 3DTeethSeg22 are research datasets with their own licenses — verify
  redistribution terms before bundling anything. Default: ship **no data**, and
  document how a user supplies their own weights.
- FDI labeling: the model must emit (or map to) the FDI values the rest of the
  app uses; reuse `tooth_values_for_arch` for the canonical order and the
  missing-teeth anchoring already in place.

## Measurement (how we prove it is better)

The realistic synthetic harness added in this branch is the gate:

- `segmentation-full-arch-accuracy`, `segmentation-realistic-arch-accuracy`
  (uneven widths + flat molar plateaus + noise), `-missing-tooth`, `-open-gap`
  in `orthoplan/validation/segmentation_cases.py` (run via `run_measurement_lab`).
- `tests/test_segmentation_real_scan.py` — the bundled-scan crown-count floor
  (14/14) and a time budget. A learned backend must **meet or beat** every floor.
- Add, when the model lands: a **boundary-smoothness / crown-compactness** metric
  (e.g. mean per-segment bounding-box aspect or surface-area-to-footprint) so the
  "rough wedge" failure mode is measurable, not just visual. The synthetic arch
  cannot fully express it; a small **labelled real-scan fixture** (PHI-free or
  consented, kept out of git or behind a flag) would be the honest benchmark.

## Integration points (checklist when building)

- [ ] `segmentation/learned.py` implementing the `segment(...)` contract via ONNX.
- [ ] Register in `load_local_segmenter()` behind an install/weights check;
      heuristic remains the fallback. Report backend in `_segmenter_metadata`.
- [ ] Optional extra in `pyproject.toml` (`onnxruntime`, `numpy`); no torch.
- [ ] Weights resolution (path/env/cache) + graceful absence.
- [ ] FDI labeling via `tooth_values_for_arch`; honour missing-teeth hints.
- [ ] New crown-compactness metric + case; keep all existing floors green.
- [ ] Docs: update this file's status and `docs/OpenAI_Agents.md` only if a
      model-provider path is involved (it is not for local ONNX).

## Risks

- **Scope creep into ML infra** — keep training out of the shipped package;
  ship inference + a contract only.
- **Weight provenance/licensing** — do not commit datasets or weights without
  clear terms.
- **Silent quality regressions** — without a real labelled fixture the synthetic
  harness can miss real-scan failure modes; treat the bundled-scan smoke test as
  necessary-but-not-sufficient.
- **Performance** — ONNX CPU inference on ~1M-vertex scans must stay within the
  existing 30 s smoke budget; may need decimation before inference.

## Estimate

Backend skeleton + ONNX wiring + fallback + tests: ~2–3 focused days assuming a
pre-trained exportable model exists. Training/curating a model from scratch is a
separate, larger effort and is **out of scope** for this integration.
