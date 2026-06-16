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
Timeline projection: 28 days (~4.0 weeks) at 14-day wear. Projection excludes refinements, compliance variation, pauses, and user-directed changes.
Data gaps: roots unavailable, CBCT unavailable, periodontal status unavailable, occlusion scan unavailable, treatment notes unavailable
Findings: 2
  - WARNING: Stage 1 exceeds configured linear cap
  - NOTICE: Movement planned without per-tooth segmentation
```

The same deterministic rules run here, in the UI (`/api/evaluate`), and in tests
- there is one engine. Timeline is an arithmetic projection, never a completion
estimate, and always carries its caveat.

## 4. Serve the UI

```bash
orthoplan serve            # http://127.0.0.1:8000
```

Serves the browser UI and the `/api/evaluate` endpoint the UI calls. See
[../ui/README.md](../ui/README.md).

## 5. Reproducible handoff report

```bash
orthoplan report examples/basic_plan.json --reviewer "Dr. Example" --out /tmp/basic-report.json
```

The report is deterministic JSON with the engine version, canonical plan hash,
stable evaluation hash, input metadata, findings, data-gap actions, timeline,
progress frames, review metadata, and a report hash. If `--signing-key-env` is
provided, the report includes an HMAC-SHA256 signature over the report hash.

## 6. Acquisition advisor

```bash
orthoplan acquisition examples/basic_plan.json
```

Ranks missing data by deterministic marginal impact: which absence-of-data
findings would clear, which currently suppressed checks would run, and which
data-gap entries would close. This toggles availability only; it predicts
nothing about what newly acquired data would show.

## 7. Measurement Truth Lab

```bash
orthoplan measurement-lab
orthoplan measurement-lab --case cumulative-translation --json
```

Runs the built-in synthetic validation cases through the same public engine paths
used by the CLI, API, reporting, and visualization frame contracts. The lab includes
file-backed golden STL fixtures plus expected millimeter/degree outputs with tolerances.
Failures print the exact expected-vs-actual mismatch.

It also includes **segmentation accuracy** cases (`segmentation-full-arch-accuracy`,
`segmentation-missing-tooth`, `segmentation-open-gap`, `segmentation-missing-tooth-marked`).
These build a synthetic arch whose per-triangle tooth membership is known by
construction, run the active on-device segmenter, and score two axes: `region_purity`
(did the cuts separate the right crowns, independent of labels) and
`triangle_label_accuracy` (did the right FDI number land on the right region).

The segmenter derives the tooth count by counting **crown peaks** in the arch's
height profile rather than assuming a full arch, so the count is right whether a
tooth is congenitally absent (`segmentation-missing-tooth`) or left an open
extraction hole filled with gum (`segmentation-open-gap`) - a gum hole has no peak,
so it never reads as an extra tooth (`tooth_count_error == 0`). Which tooth is
absent cannot be known from crown geometry, so FDI labels on a gap arch are a
positional guess until the user marks the gap; `segmentation-missing-tooth-marked`
shows that signal restoring label accuracy.

## 8. Print package export

```bash
orthoplan print-package examples/basic_plan.json --out print-output --zip --email-draft
```

Writes stage proxy STL files, a deterministic manifest, and optional zip/email
draft. The manifest binds the package to the engine version, plan hash, stage-frame
hash, artifact hashes, and geometry-source metadata. Generated files are informational
outputs from the supplied plan data and physical use is the user's own responsibility
and risk.

## 9. Labelled segmentation benchmark

```bash
orthoplan segmentation-benchmark --manifest labelled-segmentation/manifest.json
orthoplan segmentation-benchmark --manifest labelled-segmentation/manifest.json --json
```

Scores the active local segmenter against external labelled real-scan cases. The
repo does not ship patient-derived labelled scans; the manifest points to local
PHI-safe or consented fixtures and must mark each case as PHI-removed,
consent-acknowledged, and commercial-use-allowed before it is scored.

Minimal manifest shape:

```json
{
  "cases": [{
    "case_id": "non-phi-001",
    "arch": "maxillary",
    "scan_path": "case.stl",
    "labels_path": "triangle-labels.json",
    "phi_removed": true,
    "consent_acknowledged": true,
    "commercial_use_allowed": true
  }]
}
```

`triangle-labels.json` contains one FDI label per STL triangle:

```json
{ "triangle_labels": ["11", "11", "12"] }
```

The command reports triangle-label accuracy, region purity, tooth counts, and
review-burden delta versus the fallback segmenter. It is a software benchmark,
not clinical clearance.

## 10. Optional model advisory

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
approximate PCA frame metadata; rotation remains non-renderable by default).
