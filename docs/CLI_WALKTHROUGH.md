# CLI Walkthrough

The `orthoplan` CLI is the quickest way to exercise the engine without the UI.
Install first:

```bash
pip install -e .
orthoplan --version
```

All commands are deterministic and use no patient data. Output below is real
(trimmed where noted).

## 1. Create a draft plan

```bash
orthoplan new-plan --id demo-001 --title "Demo plan" --wear-interval 14
```

Prints a plan-shaped JSON document (write it with `--out plan.json`). Note the
explicit, typed `coordinate_frame` and the `movement_caps.default` heuristics:

```json
{
  "id": "demo-001",
  "title": "Demo plan",
  "numbering_system": "FDI",
  "coordinate_frame": { "name": "scan-local", "handedness": "right-handed",
    "axes": { "x": "unknown", "y": "unknown", "z": "occlusogingival" }, "...": "..." },
  "settings": {
    "movement_caps": { "default": { "linear_mm": 0.25, "angular_deg": 1.0,
      "rotation_deg": 2.0, "intrusion_extrusion_mm": 0.1, "reference": "..." },
      "per_tooth_overrides": {} },
    "timeline": { "wear_interval_days": 14 }
  },
  "scans": [], "mesh_assets": [], "tooth_meshes": [], "stages": []
}
```

## 2. Inspect an STL (metadata only)

```bash
orthoplan inspect-stl scan.stl
```

STL bytes are never stored - only redacted metadata. Units cannot be inferred
from STL, so they are `unverified` until a user confirms them:

```json
{
  "id": "c5736e1ba1ca27d5",
  "format": "stl-binary",
  "units": "unverified",
  "vertex_count": 6,
  "face_count": 2,
  "bounds": { "min_xyz": [0.0, 0.0, 0.0], "max_xyz": [40.0, 55.0, 0.0] },
  "quality": { "inspector": "internal-stl", "degenerate_faces": 0, "notes": [] },
  "reference": "scan.stl"
}

Scale note: scan units unverified; geometry scale cannot be trusted until confirmed
```

The `reference` is redacted to a basename (directories, which often carry patient
names, are stripped). With the optional `mesh` extra installed, `quality` also
reports watertight/winding status via trimesh.

## 3. Summarize a plan (runs the deterministic rules)

```bash
orthoplan plan-summary examples/basic_plan.json
```

```
Plan: Synthetic example - basic staged plan (example-basic)
Numbering: FDI  Frame: scan-local
Stages: 2  Scans: 0
Scale confirmed: True
Timeline projection: 28 days (~4.0 weeks) at 14-day wear. Projection excludes refinements, compliance variation, clinical pauses, and clinician-directed changes.
Data gaps: roots unavailable, CBCT unavailable, periodontal status unavailable, occlusion scan unavailable, clinician notes unavailable
Findings: 2
  - WARNING: Stage 1 exceeds configured linear cap
  - NOTICE: Movement planned without per-tooth segmentation
```

The same deterministic rules run here, in the UI (`/api/evaluate`), and in tests
- there is one engine. Timeline is an arithmetic projection, never a clinical
estimate, and always carries its caveat.

## 4. Serve the UI

```bash
orthoplan serve            # http://127.0.0.1:8000
```

Serves the browser UI and the `/api/evaluate` endpoint the UI calls. See
[../ui/README.md](../ui/README.md).

## 5. Optional model advisory

The advisory layer is **off by default**. It runs only when you ask for it and a
provider is configured:

```bash
pip install -e ".[providers]"
export OPENAI_API_KEY=...        # provider credentials
orthoplan advise examples/basic_plan.json --provider openai
```

Model output is parsed into a strict schema and run through the same
`lint_finding` gate as deterministic findings. Unsafe or malformed advisories are
rejected, not shown; accepted ones render with an `[ADVISORY - unverified]`
prefix. Without a provider/key it exits cleanly:

```
advise error: OPENAI_API_KEY is required for OpenAIProvider
```

Malformed plan JSON is also reported as a CLI error rather than a traceback for
both `orthoplan plan-summary` and `orthoplan advise`.

## Example plans

Two synthetic plans ship under [../examples/](../examples/README.md):
`basic_plan.json` (trips the linear cap) and `segmented_plan.json` (per-tooth
approximate frame, renderable rotation).
