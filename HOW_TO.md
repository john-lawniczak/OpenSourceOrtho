# How To Use OpenSource Ortho

OpenSource Ortho is a research/developer toolkit for staged tooth-movement planning,
measurement checks, visualization, acquisition advice, and handoff reports. It is not a
medical device and does not approve treatment.

New to dental terms (IPR, tip, torque, FDI numbering)? See the
[Glossary and tooth-numbering diagram](docs/GLOSSARY.md), also reachable in the
app from the **Key Terms** button in the sidebar. To contribute your own STL
scans and results for testing, see [Contributing Data](docs/DATA_CONTRIBUTION.md).

## 1. Start The App

```bash
/Users/johnlaw/.local/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orthoplan serve
```

Open `http://127.0.0.1:8000`.

If your default `python3` can create virtual environments correctly, `python3 -m venv .venv`
is also fine. On macOS, avoid a broken Homebrew Python 3.14 build if `ensurepip` fails;
recreate `.venv` with Python 3.11 or 3.12 instead.

## 2. Basic Workflow

The UI has two modes:

- **Guided**: educational STL review and a synthetic 12-month crowding demo for
  non-technical users.
- **Clinician**: advanced staged movement, clinical controls, findings, print
  metadata, and plan JSON.

1. Upload or reference an STL surface scan.
2. Confirm scan units before trusting millimeter measurements.
3. Declare available records: segmentation, roots, CBCT, periodontal status, occlusion,
   photos, radiographs, and treatment notes.
4. Enter staged movement values using FDI tooth IDs.
5. Review findings, data gaps, acquisition advice, timeline, progress preview, and print
   export readiness.
6. Optionally click **Generate Plan** in the Review panel to auto-build a
   cap-respecting staged plan (see *Generating a plan* below) and load it into
   the timeline.
7. Ask educational questions in **Plan AI** from the Review panel if you want a
   plain-language explanation of the current findings and limits.
8. Generate a handoff report:

```bash
orthoplan report examples/basic_plan.json --reviewer "Reviewer Name" --out report.json
```

To try the synthetic educational demo, open the app, choose **Guided**, then click
**Try 12-Month Demo**. The preview uses fabricated crowding offsets and staged
movement over one year. It is not patient-specific and does not say whether any
treatment is needed or possible.

### Generating a plan

The Review panel has a **Generate Plan** button. It builds a cap-respecting staged
plan from the best target available, in this order:

- **Authored** - if you already entered movement, it is re-split into cap-sized stages.
- **Geometry-derived** - if segmented per-tooth crowns are linked, a straightening
  target is fit from their visible positions (a geometric arch-form heuristic in
  scan-local axes; not a clinical goal and not root/bone aware).
- **Educational template** - if only a raw scan is loaded, a generic crowding
  template is used. This is **not** derived from your teeth; tick the
  acknowledgement to confirm you understand, then generate.

A deterministic orchestration step then validates the result and reports a
correctness verdict (`CONSISTENT` / `ISSUES`) - meaning the staging is internally
consistent with your caps and fixed-tooth controls, **not** that it is safe or
approved. An optional model review runs only if you select an external connector
and tick the external-agent acknowledgement; otherwise generation is fully offline.

## 3. Render Local Per-Tooth Meshes

Plan JSON stores mesh metadata and asset IDs, not mesh bytes. To render real
per-tooth STL meshes in the local UI, register each tooth STL in a local mesh
workspace and link the returned asset ID in the plan's `mesh_assets` and
`tooth_meshes`.

```bash
orthoplan register-mesh path/to/tooth_11.stl --workspace .orthoplan-meshes
ORTHOPLAN_MESH_WORKSPACE=.orthoplan-meshes orthoplan serve
```

The UI loads registered meshes from `/api/mesh/<mesh_asset_id>` and falls back
to schematic proxy teeth when a linked mesh is not available locally.

## 4. Plan AI And MCP Connectors

The Review panel includes **Plan AI**. The default connector is a local
educational helper that does not call an external service. Users can choose a
connector, enter a model preference, and add an API key for the current browser
session. The app does not write that key into plan JSON or case snapshots. Use
the context selector deliberately:

- **Summary** shares findings, data gaps, timeline, and clinical controls.
- **Clinical metadata** also shares mesh/tooth-mesh metadata.
- **Full plan snapshot** includes the full plan payload.

External connectors for OpenAI, Claude Code, MCP hosts, Odysseus, and
open-source models are listed for future configuration, but the local dev server
does not send plan context to them until an explicit provider gateway is added.
The future account-linking path should prefer OAuth or an MCP permission
handshake where a user grants a trusted agent scoped access to plan tools rather
than pasting long-lived raw keys into the app.
See `docs/AI_CHAT_MCP.md`.

## 5. Printing And Aligner Manufacturing Boundary

The app can generate stage proxy STL files, a manifest with plan/frame/artifact hashes, an
optional deterministic zip package, and an optional email draft. When segmented mesh bounds
exist, the package records that geometry source; otherwise it labels schematic proxy geometry.
Outputs are generated from the supplied plan data and are used at the user's own choice and
risk.

For physical workflows:

- Print dental models only with validated dental model resin/materials and a calibrated printer.
- Confirm units and scale before any printer-scale export.
- Remove supports, clean, cure, and smooth printed dental models according to material and
  printer instructions before thermoforming.
- Clear aligners are commonly thermoformed from selected aligner sheet materials
  such as PETG, TPU/polyurethane blends, EVA-family sheets, or other approved orthodontic
  thermoforming materials. Material choice and process validation matter.
- Do not assume ordinary hobby resin, general-purpose plastic, or an unvalidated sheet is
  safe for intraoral use.
- Do not trim, heat, polish, or otherwise alter aligner plastic unless the material
  instructions and chosen process allow it.

Any physical use is at the user's own risk and depends on validated materials, confirmed
scale, cleaning procedures, and applicable regulatory compliance.

## 6. Helpful Commands

```bash
orthoplan new-plan --id demo --out demo.json
orthoplan register-mesh path/to/tooth_11.stl --workspace .orthoplan-meshes
orthoplan register-contribution upper.stl lower.stl --arch maxillary --units mm --i-confirm-no-phi --out datasets/mine/manifest.json
orthoplan plan-summary examples/basic_plan.json
orthoplan acquisition examples/basic_plan.json
orthoplan measurement-lab
orthoplan report examples/basic_plan.json --out report.json
orthoplan print-package examples/basic_plan.json --out print-output --zip --email-draft
pytest
```

## 7. What The App Does Not Do

- It does not diagnose.
- It does not decide a plan is safe, approved, or acceptable.
- It does not infer roots, bone, periodontal status, occlusion, or treatment goals when those
  data are missing.
- It exports stage proxy STL files from the supplied plan data, not a guarantee of fit or use.
- It does not certify any manufactured aligner as safe or suitable.
- It does not let AI chat diagnose, approve treatment, or replace a licensed
  dental professional.
