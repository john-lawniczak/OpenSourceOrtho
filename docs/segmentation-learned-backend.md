# Scope: learned tooth-segmentation backend

> Status: **proposal / not yet built.** Educational tooling only — segmentation
> proposes per-tooth regions for review; it is never a diagnosis, a treatment
> decision, or a statement that care is needed, possible, safe, or complete.
>
> To start building in a fresh chat, use the paste-ready prompt in
> [segmentation-learned-backend-handoff.md](segmentation-learned-backend-handoff.md).

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

## Model availability (checked June 2026)

There is **no turnkey, license-clear ONNX tooth-segmenter** to drop in. What
exists:

- **MeshSegNet** (`Tai-Hsien/MeshSegNet`): **MIT-licensed code**, and the repo
  **ships pretrained PyTorch weights** (an upper and a lower model under
  `./models`). Caveats:
  - **No ONNX export is provided** — it is PyTorch only. Export is feasible
    (the model is PointNet++/MLP with graph-constrained "GLM" layers that take
    mesh adjacency matrices as extra inputs — exportable but fiddly), but it is a
    dev-time step, not a download.
  - **The weights' license is undocumented.** MIT covers the *code*; the bundled
    models were trained on a **private clinical IOS dataset** (Lian et al.), and
    the repo says nothing about redistribution/commercial terms for the *weights*.
    Clear this before shipping or redistributing them.
  - **Non-trivial preprocessing:** decimate the mesh to **<= 10k cells**, build
    **15-dim per-cell features** (9 vertex coords + 3 normal + 3 relative
    position), **per arch**, **15 classes** (14 teeth + gingiva) -> map to FDI ->
    back to `ToothSegment` triangles.
- **Teeth3DS+ / 3DTeethSeg'22** dataset (1800 scans / 900 patients, public on
  OSF): **CC BY-NC-ND 4.0 — non-commercial, no derivatives.** Training our own
  model on it inherits NC/ND terms, which is **incompatible with an openly /
  commercially reusable build.** Do not bake it in.
- **DilatedToothSegNet** (2024) is a newer mesh model worth evaluating as an
  alternative if MeshSegNet export is painful; license/ONNX status unconfirmed.

Sources: github.com/Tai-Hsien/MeshSegNet (+ its MIT LICENSE), arXiv:2109.11941,
crns-smartvision.github.io/teeth3ds, 3dteethseg.grand-challenge.org,
arXiv:2305.18277, DilatedToothSegNet (Springer 10.1007/s10278-024-01061-6).

## Candidate approaches (in rough order of effort)

1. **Export the MIT MeshSegNet PyTorch weights to ONNX** (dev-time, torch only
   at export, not at runtime), run via `onnxruntime` (CPU). Fastest path to a
   real model, BUT gated on (a) clearing the weights' license and (b) the
   adjacency-matrix export + per-cell preprocessing work.
2. **A lighter PointNet++/DGCNN-style face classifier** trained on a
   license-clear dataset — smaller, simpler to export, but needs training.
3. **Geometry upgrade, no ML:** curvature/normal-based watershed on the mesh
   graph (needs the half-edge adjacency we do not currently build). Cleaner cuts
   than the 1-D heuristic without weights, but well short of a trained model.

Recommendation: **(1) export MeshSegNet to ONNX** as the model spike (after
Phase 1), with the heuristic retained as the always-available fallback and the
weights supplied by the user (never committed), which sidesteps both the
file-size and the redistribution-license problems.

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

- **MeshSegNet weights** (if used): MIT code, but the bundled models were trained
  on a private clinical dataset with **no stated weights license**. Confirm
  redistribution/commercial terms before shipping; default to **user-supplied
  weights** (a path/env var) so the project never redistributes them.
- **Teeth3DS+ / 3DTeethSeg'22** is **CC BY-NC-ND 4.0** (non-commercial, no
  derivatives). A model trained on it cannot be used in a commercially reusable
  build — do not train on it for the shipped backend. Default: ship **no data**.
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

- **Phase 1** (contract + loader/fallback + `ml-seg` extra + compactness metric +
  tests; *no model*): ~1–2 focused days, no external dependency.
- **Model spike** (export MeshSegNet -> ONNX, per-cell preprocessing, FDI mapping,
  beat the harness floors): ~2–4 days, **gated on clearing the weights' license**.
  Note: MeshSegNet's GLM layers take mesh adjacency matrices as inputs, so the
  ONNX export and the decimate-to-<=10k-cells preprocessing are the real work.
- **Training a model from scratch** (e.g. on a license-clear dataset): a separate,
  larger effort, **out of scope** here.
