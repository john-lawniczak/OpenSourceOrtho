# Phase 2 UI Prototype

Browser prototype for the data-model workflow:

1. STL upload metadata
2. data availability toggles
3. movement cap controls
4. stage movement table
5. timeline projection
6. progress preview
7. plan-shaped JSON output

## Run it

The UI is backed by the Python engine and must be served by the dev server so
it can reach `POST /api/evaluate`:

```bash
python3 -m orthoplan.server        # or: orthoplan serve
```

Then open `http://127.0.0.1:8000`.

## Engine is the single source of truth

The UI does **not** compute findings, data gaps, the timeline, or cumulative
tooth poses itself. On every edit it sends the plan-shaped JSON to
`POST /api/evaluate`, and renders exactly what `orthoplan.api.evaluate_plan`
returns — the same deterministic rules, lint-gated findings (with their data
gap and clinician question), timeline projection, and `StageProgressFrame`
data used everywhere else. Cumulative movement in the canvas comes from the
engine's frames, and rotation is shown only as tabular values because the
Phase 1 scan frame reports `rotation_renderable=false`.

If the engine is unreachable (e.g. the page was opened via `file://`), the UI
shows an "engine offline" message instead of silently falling back to a second,
divergent implementation.

Browser STL metadata is approximate; `orthoplan.io.stl_import.inspect_stl()`
remains the source of truth for mesh inspection.

## Tests

Pure, DOM-free UI logic lives in `core.js` (HTML escaping, contiguous stage
reindexing, frame pose extraction, the async stale-response token guard) so it
can be unit-tested under Node with no browser or jsdom:

```bash
cd ui && node --test        # or, from the repo root: node --test 'ui/*.test.js'
```

The DOM modules (`render.js`, `plan.js`) import these helpers from `core.js`
rather than defining them inline, so the tested code is the shipped code.

