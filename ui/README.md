# Phase 2 UI Prototype

Static browser prototype for the data-model workflow:

1. STL upload metadata
2. data availability toggles
3. movement cap controls
4. stage movement table
5. timeline projection
6. progress preview
7. plan-shaped JSON output

Run locally:

```bash
python3 -m http.server 4173 --directory ui
```

Then open `http://localhost:4173`.

The prototype is client-side only. Browser STL metadata is approximate; backend `orthoplan.io.stl_import.inspect_stl()` remains the source of truth for mesh inspection.

