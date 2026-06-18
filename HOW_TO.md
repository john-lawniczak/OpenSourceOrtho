# How To Use OpenSource Ortho

OpenSource Ortho is a clear-aligner planning safety playground and research/developer
toolkit for staged geometry, measurement checks, visualization, acquisition advice,
and handoff reports. It is not a medical device, not complete treatment-planning
software, and not a substitute for a licensed dental professional. It does not
diagnose, prescribe, approve treatment, authorize physical use, or make any
generated appliance safe. Any use, manufacturing, or physical application of outputs
is entirely at the user's own responsibility and risk.

New to dental terms (IPR, tip, torque, FDI numbering)? See the
[Glossary and tooth-numbering diagram](docs/GLOSSARY.md), also reachable in the
app from the **Key Terms** button in the sidebar. To contribute your own STL
scans and results for testing, see [Contributing Data](docs/DATA_CONTRIBUTION.md).

## 1. Start The App

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orthoplan serve
```

Open `http://127.0.0.1:8000`.

If your default `python3` can create virtual environments correctly, `python3 -m venv .venv`
is also fine. On macOS, avoid a broken Homebrew Python 3.14 build if `ensurepip` fails;
recreate `.venv` with Python 3.11 or 3.12 instead.

## 2. Basic Workflow

The app opens in **Guided** mode by default. Switch between modes with the
**Guided / Technician** toggle on the left sidebar (a light/dark switch sits in
the top bar):

- **Guided**: a six-step wizard for non-technical users -
  **Upload → Teeth & time → Details → Review → 3D preview → Print / send** -
  with Back/Next and a progress rail. Choose which teeth move and how long each
  tray is worn, build the plan, watch it animate in 3D, ask the AI about it, and
  export printable files. These outputs are for review only and do not authorize
  treatment or physical use.
- **Technician**: advanced staged movement, clinical controls, findings, print
  metadata, and plan JSON.

To see a complete, isolated example, click **Sample Test Case** in the left
sidebar: it runs the guided wizard pre-loaded with the two bundled test-case STL
scans, redacted CBCT metadata, a safe root/bone engineering fixture, and a
Balanced 10-day pace, starting at step 1 so you can walk the whole flow. The 3D
preview shows the real scans with sample-only per-tooth segmentation and the
root/bone-aware fixture path: accepted fixture STL-to-CBCT registration, trusted
derived root/axis landmarks, anatomical frames, root/bone context, and CBCT
boundary priors. This is a workflow fixture, not clinical interpretation of raw
CBCT. It snapshots and restores your own work, so nothing leaks into your
editors; use **Exit Sample Test Case** to return.

The Technician workflow:

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

In the 3D preview you can toggle **Tooth #** to overlay FDI tooth numbers on each
tooth, which helps when choosing which teeth to move.

### Auto-segmenting teeth (experimental)

A whole-arch STL is one shell, not per-tooth meshes, so real per-tooth planning
needs segmentation. In the **Technician** Review side panel, **Auto-Segmentation
(experimental)** proposes per-tooth regions from a loaded server-local scan (the
Sample Test Case / example scans) via `POST /api/segment`. It uses local hybrid
geometry cues: arch position, crown-height valleys, curvature, and face-normal
changes. It runs on this machine (scans are PHI; nothing is sent off-device).
The result is a **draft**: review the per-tooth confidence, correct each FDI number, include/exclude teeth, then
**Apply accepted segmentation to plan** - nothing is auto-applied. It is not a
diagnosis and does not indicate whether treatment is needed or possible.
When a plan carries trusted, gate-passing CBCT-derived anatomy, the segmenter may
also report `cbct_prior` boundary priors. These bias and score the draft cuts;
they do not replace review.

### Generating a plan

The Review panel has a **Generate Plan** button. It builds a cap-respecting staged
plan from the best target available, in this order:

- **Authored** - if you already entered movement, it is re-split into cap-sized stages.
- **Geometry-derived** - if segmented per-tooth crowns are linked, a straightening
  target is fit from their visible positions (a geometric arch-form heuristic in
  scan-local axes; not a clinical goal and not root/bone aware).
- **Root/bone-aware context** - when registered, reviewed CBCT-derived anatomy is
  present, evaluation adds root/bone context, anatomical frames, and proximity
  checks. Generation still remains a proposal and never becomes clinical
  approval.
- **Educational template** - if only a raw scan is loaded, a generic crowding
  template is used. This is **not** derived from your teeth; tick the
  acknowledgement to confirm you understand, then generate.

A deterministic orchestration step then validates the result and reports a
correctness verdict (`CONSISTENT` / `ISSUES`) - meaning the staging is internally
consistent with your caps and fixed-tooth controls, **not** that it is safe or
approved.

**Notes for the AI review**: the Generate Plan panel has a free-text *Notes* box.
Anything you write there (for example, "focus on the lateral incisors FDI 12 and
22 — they are off-plane") is **always acted on**: with an external connector the
notes are appended to the model review prompt; with the default offline local
helper, a deterministic, linted educational note reflects your focus back and
relates it to what the plan actually moves. Notes never change the deterministic
staging or relax the safety boundary, and any model output still passes the lint
gate.

**Precise landmarks**: the best way to ground the plan in your real teeth is to
import per-tooth crown landmarks. Get a fill-in template with `orthoplan
landmarks-template --out landmarks.json`, fill each tooth's occlusal-plane (x, y)
in millimeters from the scan, then import it with the *Import landmarks* control
in the Generate Plan panel. With landmarks present, generation is
"landmark-derived" (real arch-form targets + IPR space budget + collision check).

**Connecting an AI model / API key**: the optional review reuses the connector you
configure in the **Plan AI** box (same Review surface). The provider selector and
the **API key** field are shown directly in that box - pick a provider (OpenAI,
Claude, MCP/Odysseus/open-source) and paste a session-only key; the key field is
hidden for the no-key local helper. Agent/MCP-endpoint and the
*Allow an external AI agent…* consent live under **Advanced connector settings**.
The Generate Plan panel shows which connector is active. With the default
**local helper** (or no consent), the AI review is skipped and generation runs
**fully offline** - the deterministic plan is still produced.

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

### Saving plan versions

The Review panel's **Versions** section saves named snapshots of the current
plan (the case is keyed by Plan ID) and can restore any version back into the
editor. Versions persist locally via the dev server in `.orthoplan-cases.json`
(override the path with `ORTHOPLAN_CASE_STORE`). The same history is available
from the CLI with `case-save`, `case-list`, and `case-versions`.

## 4. Plan AI And MCP Connectors

The Review surface includes **Plan AI**. The default connector is a local
educational helper that does not call an external service. The **provider
selector and a session-only API-key field are shown directly in the AI box**
(with provider-specific instructions; the key field is hidden for the local
helper, which needs none). The app does not write that key into plan JSON, case
snapshots, or `localStorage`. Use the context selector deliberately:

- **Summary** shares findings, data gaps, timeline, and clinical controls.
- **Clinical metadata** also shares mesh/tooth-mesh metadata.
- **Full plan snapshot** includes the full plan payload.

External connectors for OpenAI, Claude (Anthropic), MCP hosts, Odysseus, and
open-source models perform live completions once you select the provider, paste a
key/endpoint, and grant per-session egress consent (`share_acknowledged`); the
key is transmitted only to the selected connector and only when you press
**Ask AI**. The future account-linking path should prefer OAuth or an MCP
permission handshake where a user grants a trusted agent scoped access to plan
tools rather than pasting long-lived raw keys into the app.
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
  such as PETG, TPU/polyurethane blends, EVA-family sheets, or other clinician-selected
  orthodontic thermoforming materials. Material choice and process validation matter.
- Do not assume ordinary hobby resin, general-purpose plastic, or an unvalidated sheet is
  safe for intraoral use.
- Do not trim, heat, polish, or otherwise alter aligner plastic unless the material
  instructions and chosen process allow it.

Any printing, thermoforming, wearing, or other physical use is at the user's own
responsibility and risk and depends on validated materials, confirmed scale,
cleaning procedures, professional supervision, and applicable regulatory compliance.
The software provides no warranty that a generated model, aligner, or package is
safe, effective, legal, fit for use, or suitable for any person.

## 6. Helpful Commands

```bash
orthoplan new-plan --id demo --out demo.json
orthoplan register-mesh path/to/tooth_11.stl --workspace .orthoplan-meshes
orthoplan register-contribution upper.stl lower.stl --arch maxillary --units mm --i-confirm-no-phi --out datasets/mine/manifest.json
orthoplan case-save examples/basic_plan.json --note "first pass"
orthoplan case-list
orthoplan case-versions example-basic
orthoplan landmarks-template --arch both --out landmarks.json
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
- It does not produce or claim to produce a complete treatment plan.
- It does not infer roots, bone, periodontal status, occlusion, or treatment goals when those
  data are missing.
- It exports stage proxy STL files from the supplied plan data, not a guarantee of fit or use.
- It does not certify any manufactured aligner as safe or suitable.
- It does not authorize printing, wearing, or physically applying any output.
- It does not let AI chat diagnose, approve treatment, or replace a licensed
  dental professional.
