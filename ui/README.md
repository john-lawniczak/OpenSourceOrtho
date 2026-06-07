# Phase 2 UI Prototype

![Stage builder](../docs/images/stage-builder.png)
![3D progress review](../docs/images/review-3d.png)

Browser prototype for the data-model workflow:

1. Guided six-step wizard (default) + isolated Sample Test Case demonstration
2. multi-file STL upload metadata with browser-side upload persistence
3. data availability toggles
4. movement cap controls
5. stage movement table
6. timeline projection
7. progress preview
8. scoped Plan AI chat
9. plan-shaped JSON output
10. print-export readiness and package metadata

## Run it

The UI is backed by the Python engine and must be served by the dev server so
it can reach `POST /api/evaluate`:

```bash
python3 -m orthoplan.server        # or: orthoplan serve
```

Then open `http://127.0.0.1:8000`.

The app opens in Guided mode by default. A light/dark switch is anchored at the
top-right of the window in every mode. The sidebar **Sample Test Case** button
opens an isolated walkthrough that reuses the guided wizard, pre-loaded with the
two bundled test-case STL scans; it snapshots and restores the user's working
state, so it never replaces the normal Guided or Technician flows. The same button
becomes **Exit Sample Test Case** while the sample is active, and the
Guided/Technician toggle stays available throughout so the sample can be viewed in
either mode.

## Modes

The sidebar **Guided / Technician** toggle (always visible on the left) exposes two
workflows:

- **Guided** (default) is a six-step wizard for non-technical users -
  **Upload → Teeth & time → Details → Review → 3D preview → Print / send** - with
  a progress rail and Back/Next, showing one step at a time. It lets a user upload
  an STL, choose which teeth move and the tray-wear pace (Balanced 10-day by
  default, with Faster/Gentle behind a disclosure), build the plan, review it as a
  plain-language summary with a prominent Ask-AI box, preview it in 3D, and export
  printable files. It acknowledges that the preview is not a diagnosis or treatment
  plan.
- **Technician** is the advanced workspace for records, caps, staged movement,
  clinical controls, print metadata, optimized staging, and plan JSON.

The Sample Test Case renders the exact bundled STL models
(`example-scans/canonical-orthocad-001/sample-test-case-{upper,lower}.stl`); the
per-tooth movement layer over a whole-arch shell is schematic.

The 3D viewer, AI box, and upload control are single instances relocated into the
active surface (delegated events + id-based renders), so there is never a second
WebGL context.

## Plan AI

The Review surface includes a prominent **Ask AI about your plan** box. It posts
the current plan-shaped JSON to `POST /api/chat` with a selected connector, model
preference, and context scope. The default `local` connector produces an
educational explanation without leaving the local server. External connectors for
OpenAI, Claude (Anthropic), MCP hosts, Odysseus, and open-source models perform
live completions once a provider is selected, a key/endpoint is supplied, and
per-session egress consent (`share_acknowledged`) is given.

The **provider selector and a session-only API-key field are shown directly in
the AI box** with provider-specific, plain-language help (the key field is hidden
for the no-key local helper); the agent/MCP endpoint and egress consent live under
**Advanced connector settings**. API keys are read only at send time and are not
written into plan JSON, case snapshots, `localStorage`, or exported reports.

Context scopes:

- **Summary**: findings, data gaps, timeline, and clinical controls.
- **Clinical metadata**: summary plus mesh/tooth-mesh metadata.
- **Full plan snapshot**: the complete plan payload.

## Engine is the single source of truth

The UI does **not** compute findings, data gaps, the timeline, or cumulative
tooth poses itself. On every edit it sends the plan-shaped JSON to
`POST /api/evaluate`, and renders exactly what `orthoplan.api.evaluate_plan`
returns - the same deterministic rules, lint-gated findings (with their data
gap and follow-up question), data-gap actions, timeline projection, and
acquisition advice, timeline projection, and `StageProgressFrame` data used
everywhere else. Cumulative movement in the canvas comes from the engine's
frames, and rotation is shown only as tabular values unless the engine receives
a trusted non-approximate anatomical frame.

If the engine is unreachable (e.g. the page was opened via `file://`), the UI
shows an "engine offline" message instead of silently falling back to a second,
divergent implementation.

Browser STL metadata is approximate; `orthoplan.io.stl_import.inspect_stl()`
remains the source of truth for mesh inspection. Uploaded STL files are stored
locally in IndexedDB so a small upper/lower scan set survives reloads on the
same browser; they are not uploaded to a server database.

## Canonical scan fixture

`ui/example-scans/canonical-orthocad-001/` contains upper and lower whole-arch
OrthoCAD shell STLs (`sample-test-case-{upper,lower}.stl`) used to keep exact scan
rendering stable as the product evolves (and as the first tracked data
contribution). You can load them via the normal upload control to see exact
whole-arch scan rendering. The sidebar **Sample Test Case** loads these same two
STLs as its already-present records and renders them in an overlay view, with a
simulated tooth-movement layer animating across stages; the per-tooth movement
over a whole-arch shell is schematic.

## 3D viewer

The Progress Preview renders in 3D via Three.js (`viewer3d.js`), with a 2D/3D
toggle (2D canvas is the fallback when WebGL is unavailable). Important honesty
constraints, surfaced in the on-screen caveat:

- It renders registered local STL tooth meshes when `render_meshes` links are
  available from the Python API. Otherwise it falls back to schematic proxy teeth.
  Plan JSON still does not store mesh bytes; local mesh serving is limited to
  `/api/mesh/<mesh_asset_id>` files registered in the local mesh workspace.
- Uploaded or canonical whole-arch STL scans render as an exact enamel-colored
  scan layer in Current and Overlay views. Current schematic proxy teeth are hidden
  when that exact scan layer is present, so the user is not shown two competing
  "current" anatomies.
- Whole-arch scans are rotated from common STL dental coordinates into the viewer
  frame (`x, y, z` -> `x, z, -y`) so the occlusal plane lies on the 3D grid and
  tooth height points upward.
- Translation is exact but **exaggerated** by the on-screen ×factor so sub-mm
  movement is visible next to ~10 mm teeth.
- Rotation is drawn **only** where the engine sets `rotation_renderable`. The
  approximate crown-surface PCA frame (`tooth_frames` in the API) is metadata
  only; by itself it does not authorize rendered rotation.
- A **Tooth #** toolbar toggle overlays FDI tooth-number badges on each tooth so a
  user can see which teeth they are focusing on. It is off by default and follows
  the displayed (current or planned) tooth position.

Three.js (r169, MIT) is **vendored** under `ui/vendor/` and loaded via an import
map, so the app runs fully offline with no runtime calls to any external host.
To update it, replace `ui/vendor/three.module.js` and `ui/vendor/OrbitControls.js`
with a matching pinned pair.

## Auto-segmentation (experimental)

A whole-arch STL is a single shell, not per-tooth meshes, so real per-tooth
planning needs segmentation. The Technician Review side panel **Auto-Segmentation
(experimental)** proposes per-tooth regions from a loaded server-local scan via
`POST /api/segment`:

- It runs **on this machine** (scans are PHI; segmentation never calls a hosted
  API). Today the local model is a dependency-free **valley-based heuristic**
  (`orthoplan/segmentation/heuristic.py` + `arch_profile.py`): it walks the arch
  and cuts at the height valleys between crowns (balanced by equal spacing, then
  snapped to the nearest real gap). `orthoplan/segmentation/auto.py` is the seam
  where an on-device learned model (e.g. Teeth3DS / MeshSegNet) can be dropped in
  behind the same contract.
- The response is a **draft proposal**, never auto-applied: per-tooth confidence
  (separation, not certainty), advisory model-provenance findings (all pass
  `lint_finding`), and a ready-to-merge plan fragment (`mesh_assets` +
  `tooth_meshes`). Each proposed tooth mesh is written into the local mesh
  workspace and served by `/api/mesh/<id>`.
- The UI lets the user correct each tooth number and include/exclude teeth, then
  **explicitly** apply the accepted set; only then does `plan.js` merge it into the
  plan. It only operates on server-local scans (the Sample Test Case / example
  scans), because uploaded bytes stay in the browser.

## Print Export

The Settings step has print-export fields for format, delivery email, dental model
material, thermoforming material, and acknowledgement. The Review step renders backend
readiness status from `print_export`. The guided **Print / send** step builds the
files in-browser via `POST /api/print-package` (which reuses `export_print_package`)
and offers a zip download plus an `.eml` draft that opens pre-attached in a mail
client. The same package is available from the CLI: `orthoplan print-package`
generates stage proxy STL files, a hash-bound manifest, optional deterministic zip
package, and optional email draft from the supplied plan data.

## Tests

Pure, DOM-free UI logic lives in `core.js` (HTML escaping, contiguous stage
reindexing, frame pose extraction, the async stale-response token guard) so it
can be unit-tested under Node with no browser or jsdom:

```bash
cd ui && node --test        # or, from the repo root: node --test 'ui/*.test.js'
```

The DOM modules (`render.js`, `plan.js`) import these helpers from `core.js`
rather than defining them inline, so the tested code is the shipped code.

A headless-browser smoke/visual-regression test (`tests/e2e/test_viewer_smoke.py`)
verifies the 3D viewer mounts a sized WebGL canvas, the acquisition panel renders,
print export readiness is visible, 2D/3D screenshot artifacts are non-empty, the 2D
canvas has non-background movement pixels, and invalid stage input reaches both the
machine-readable API rejection state and visible engine rejection state. It is skipped
unless Playwright is installed:

```bash
pip install -e ".[e2e]" && python -m playwright install chromium
pytest tests/e2e -q
```

All three suites (Python, JS, e2e) run in CI on every push and pull request.

The screenshots above are generated headlessly (no patient data) and can be
regenerated after UI changes:

```bash
pip install -e ".[e2e]" && python -m playwright install chromium
python tools/capture_screenshots.py    # writes docs/images/*.png
```
