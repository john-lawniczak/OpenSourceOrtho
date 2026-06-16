# OpenSource Ortho

OpenSource Ortho is an open-source clear-aligner planning safety playground and research toolkit. It supports surface-based STL planning experiments today; reviewed CBCT/DICOM-derived anatomy is a higher-fidelity path for root/bone-aware checks, not a claim that the software produces a complete treatment plan.

Created by John Lawniczak with the goal of making clear-aligner planning tools
more transparent, inspectable, and patient-data-portable.

[![OpenSource Ortho review workspace](docs/images/sample-workspace.png)](docs/media/sample-demo.mp4)

> The Review workspace: a stacked **Upper arch / Lower arch** 3D preview with
> loaded crown meshes, staged movement, crown-proximity overlays, findings, and
> data gaps. ▶ [Watch the demo (MP4)](docs/media/sample-demo.mp4).

## Mission

**Everyone deserves the right to their own data and access to a healthy, clean smile.**

Orthodontic planning is dominated by closed, expensive, proprietary systems that
lock patients out of their own scans and treatment data. OpenSource Ortho exists
to change that: a transparent, inspectable, community-owned toolkit where the
math is auditable, the data stays with the person it belongs to, and the safety
boundaries are explicit rather than hidden. The product north star is to cover as
much of the modern clear-aligner treatment workflow as can be built lawfully,
openly, and safely: scan intake, segmentation, target setup, 3D controls,
side-by-side plan comparison, live restaging, root/bone-aware review, staged
exports, manufacturing-oriented QA, monitoring records, and retention handoff.
The current build is not distributed as a medical device, is not complete
treatment-planning software, and does not replace a licensed professional.

Most project documentation lives in [docs/](docs/README.md), including the
current [application maturity](docs/application%20maturity.md) scorecard.

New users can start with [HOW_TO.md](HOW_TO.md).

The first static UI prototype lives in [ui/](ui/README.md).

Scaffolding for the **lite** iOS and Android apps - thin native clients over the
same engine - lives in [mobile/](mobile/README.md).

The UI opens by default into a guided, step-by-step experience; the dense
technician workspace is one click away via the **Guided / Technician** toggle in
the left sidebar. A light/dark switch is anchored in the top bar.

## Quick Context For AI Assistants

If you open this repo in an IDE and ask an AI model for help, give it this
context first:

- This is an open-source clear-aligner planning **research toolkit and safety
  playground**, not medical-device software and not a treatment recommendation
  engine.
- The app's core job is to ingest dental mesh records, build/review staged
  tooth-movement proposals, visualize them in 3D, expose data gaps, and export
  reproducible handoff/print artifacts with provenance.
- The key safety rule is fail-closed honesty: missing roots, bone, occlusion,
  scale, periodontal status, or reviewed anatomy must stay visible as data gaps;
  the app must never convert a preview into "safe", "approved", or "complete".
- Browser UI code lives in [ui/](ui/README.md). Python engine/API/CLI code lives
  in [orthoplan/](orthoplan). Native lite clients live in [mobile/](mobile/README.md).
  Architecture, safety, data contribution, AI-chat, and maturity docs live in
  [docs/](docs/README.md).
- Active implementation work is tracked only in [TODO.md](TODO.md). Completed
  history should be read from git history and the feature docs, not treated as
  unfinished work.
- The most useful contributions are privacy-safe longitudinal STL
  (stereolithography) scan bundles, reviewed segmentation/setup improvements,
  UI tests, safety-boundary hardening, and docs that help non-specialists
  understand their own data. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and
  [docs/DATA_CONTRIBUTION.md](docs/DATA_CONTRIBUTION.md).

- **Guided mode (default)**: a six-step wizard for non-technical users -
  **Upload → Teeth & time → Details → Review → 3D preview → Print / send**. It
  explains limits in plain language, lets you choose which teeth move and how
  long each tray is worn, animates the plan in 3D, surfaces a prominent
  **Ask AI about your plan** box, and exports printable files. It is designed to
  produce questions for a dental professional, not a do-it-yourself treatment plan.
- **Technician mode**: a professional planning workspace for staged movement, records,
  clinical controls, findings, mesh rendering, print metadata, and plan JSON.
- **Sample test case**: a fully isolated walkthrough that reuses the guided wizard
  (same step chips), pre-loaded with the two bundled test-case STL scans and a
  Balanced 10-day pace. It starts at step 1 so a first-time viewer can walk the
  whole flow, and it renders the real scans in 3D (the per-tooth movement layer is
  marker/schematic until reviewed per-tooth meshes are applied). It snapshots and
  restores your working state, so opening it never changes your own plan, uploads,
  or editors.
- **Print / send**: the final guided step builds printable 3D files (one model
  per stage plus a manifest) via `POST /api/print-package` and offers a zip
  download and a pre-filled email draft (`.eml`) you can open in your mail app to
  send the files to yourself or a print service.
- **Auto-segmentation (experimental)**: an on-device hybrid geometry segmenter
  proposes per-tooth meshes from a whole-arch scan via `POST /api/segment`.
  It uses arch position, height valleys, curvature, and face-normal changes to
  choose graph-cut-style boundaries, with optional Open3D mesh-processing support.
  It is a reviewable draft with per-tooth confidence - you correct the FDI numbers
  and **explicitly** apply it; nothing is auto-accepted, and scans never leave the
  machine. A `SegmentationModel` seam lets a local learned model (e.g. Teeth3DS)
  replace the geometric proposal later.
- **Generate Plan**: a one-click pipeline (the guided **Build my plan** button,
  and the Technician Review panel) that builds a
  cap-respecting staged plan from the best available target - your authored
  movement; per-tooth crown **landmarks** (real arch-form deviation targets plus a
  space analysis that budgets IPR, adds attachments, and checks crown collisions);
  segmented crown geometry; or, if only a raw scan is loaded, a clearly-labeled
  educational template. A deterministic orchestration step runs explicit named
  checks and a verdict (`CONSISTENT`/`ISSUES`, never "safe"/"approved"); an
  optional model review is consent-gated and linted. It is a proposal, not a
  diagnosis or treatment approval.
- **Safety-review tiers**: STL-only users get a first-class **Surface Review** based on
  visible crown geometry. CBCT/DICOM is not required for every user; it is the
  higher-fidelity path toward **Root/Bone-Aware Review** when the record is
  locally ingested, registered to the STL, segmented/reviewed, and validated. See
  [docs/cbct-evaluation.md](docs/cbct-evaluation.md).
- **Plan versions and setup comparison**: save named snapshots of a plan, restore
  any version back into the editor, compare captured/saved/current/generated
  setups side by side, live-restage an edited candidate, and promote a compared
  setup only after an explicit user action. Compared setups carry provenance
  labels such as manual, generated, saved version, restored version, or imported
  plan.
- **Direct 3D controls**: technician controls can author review-gated geometric
  proposals for translation, intrusion/extrusion, rotation, crown tip, crown
  torque, crown angulation, arch expansion/contraction, attachment/IPR/spacing
  metadata, tooth locking, and movement exclusions. These controls stay
  proposals until deterministic checks and human review run, and fail closed
  when scale, reviewed segmentation, roots, or reviewed anatomy are missing.
- **Plan AI chat**: a scoped advisory chat panel that can explain the current
  plan context, findings, data gaps, and timeline. The AI box shows a **single
  model dropdown** (each option carries its provider) and an **API-key field with
  plain-language instructions**, so it is obvious how to enable a real model; the
  key field is hidden for the **local helper**, which works without any key or
  external service. Live connectors for OpenAI (GPT), Claude (Anthropic), and any
  OpenAI-compatible host (MCP / open-source / self-hosted local models) are
  available and gated behind explicit per-session consent that data leaves the
  machine. The chat always sends the full plan context. The key is read only when
  you press **Ask AI** and is never persisted.

It is not an autonomous diagnostic system, clinical approval system, or complete treatment-planning system. The project focuses on geometric representation, configured-rule checks, staged tooth-movement proposals, visualization, printable package generation, and advisory evaluation under explicitly declared data limitations. Any physical use is the user's own responsibility and risk. The software and outputs are provided without warranty or liability for diagnosis, treatment, manufacturing, fit, materials, injury, regulatory compliance, or other use. The roadmap intentionally separates STL-only surface review from CBCT/DICOM-enhanced root/bone-aware review.

Visual progress representation is a first-class requirement. The UI must accurately show staged tooth movement, data gaps, units, and provenance without implying approval. See [docs/UI_DESIGN.md](docs/UI_DESIGN.md).

## Boundary

The software may:

- represent proposed tooth movements and staged aligner-style plans
- import, export, and visualize dental mesh data
- attach and visualize CBCT/DICOM records when that roadmap phase ships
- check internal consistency against user-configured movement caps
- surface observational findings, data gaps, and handoff questions
- rank missing data by deterministic acquisition impact
- run local or explicitly configured remote model providers for advisory review
- open an auditable, scoped AI chat session over selected plan context
- generate reproducible handoff reports tying inputs to engine version and findings

The software may not:

- diagnose disease or malocclusion
- decide whether treatment is safe, suitable, approved, or complete
- produce or claim to produce a complete treatment plan
- infer unseen anatomy such as roots, bone, periodontal status, or CBCT findings when those records or reviewed derived anatomy are unavailable
- invent unsupported thresholds
- replace user judgment, consent, responsibility, or regulatory obligations

See [docs/SAFETY.md](docs/SAFETY.md) before using or contributing.

## How It Works

The first workflow is simple:

1. Upload an STL intraoral scan.
2. Segment the arch into individual tooth meshes.
3. Create a staged `TreatmentPlan` with per-tooth movement deltas.
4. Check each stage against user-configured movement caps.
5. Render cumulative progress frames in the UI.
6. Export a reproducible handoff report that clearly separates rule checks, model advisories, data gaps, and provenance.

CBCT/DICOM support is tiered: local record metadata intake, on-device viewing
handoff, STL-to-CBCT registration records, reviewed anatomy representation,
root/bone-aware checks when trusted anatomy exists, and manufacturing manifests
that label the review tier, unresolved data gaps, and user responsibility for any
physical use. Local raw-volume sparse-mask root/bone proposals and automatic
STL-to-CBCT registration proposals exist, but they remain untrusted until
explicit human review/acceptance; a bundled clinical-grade CBCT segmentation
model remains out of scope for the core install.

For a quick demo, open the app and click **Sample Test Case** in the left
sidebar. The sample reuses the guided wizard, pre-loaded with the two bundled
test-case STL scans (`ui/example-scans/canonical-orthocad-001/`), and starts at
step 1 so you can walk the whole flow. The 3D preview renders the real scans and
clearly labels whether staged movement is schematic/marker-based or backed by
reviewed per-tooth STL fragments. Drag the stage slider, or use **Play**, to watch
the planned movement across stages. Use the on-screen **＋ / ⌂ / −** controls (or
scroll/drag) to zoom and orbit, the **Tooth #** toggle to label teeth, and **Exit
Sample Test Case** to return - your own work is untouched.

In the guided **Review** step (or the Technician Review panel), use **Plan AI** to
ask educational questions about the active plan. The default local helper stays on
this machine and needs no key. To use an external model, pick it from the single
**model dropdown** (e.g. GPT-5.5, Claude Opus 4.8, or an open-source / self-hosted
endpoint) in the AI box and paste your API key in the field shown there; the model
endpoint and egress-consent options live under **Connector settings**. The key is
read only when you press **Ask AI**; it is never written to plans, case snapshots,
or `localStorage` and is never echoed back by the server. See
[docs/AI_CHAT_MCP.md](docs/AI_CHAT_MCP.md).

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the plain-language system overview.

## Maintainability

The project should stay modular and composable as it grows. Follow [docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md) for file-size guardrails, directory ownership, review checklist, and the maintainability check script.

## Repository Map

- [orthoplan/model/](orthoplan/model) - typed plan, geometry, asset, dataset,
  review-tier, anatomy, and contribution-manifest models.
- [orthoplan/planning/](orthoplan/planning) - staging, transforms, timeline, and
  setup-generation logic.
- [orthoplan/evaluation/](orthoplan/evaluation) - deterministic rule checks,
  data-gap logic, acquisition advice, and linted model-advisory boundaries.
- [orthoplan/segmentation/](orthoplan/segmentation) - local heuristic and
  optional learned segmentation contracts.
- [orthoplan/server.py](orthoplan/server.py) and [orthoplan/api.py](orthoplan/api.py)
  - local HTTP boundary and pure evaluation API used by the browser.
- [ui/](ui/README.md) - guided and technician browser workspace, 3D viewer, setup
  comparison, glossary, and local upload handling.
- [mobile/](mobile/README.md) - iOS and Android lite clients over the same
  educational review concepts.
- [shared/glossary.json](shared/glossary.json) - shared glossary source generated
  into web, iOS, and Android by [tools/sync_glossary.py](tools/sync_glossary.py).
- [tests/](tests) and [ui/*.test.js](ui) - Python and browser-unit coverage.

## References

Commercial clear-aligner and dental-planning systems may be studied as workflow references only. Do not fork, copy, reverse engineer, or import proprietary source, assets, terminology, or private workflows. See [docs/OPEN_SOURCE_REFERENCES.md](docs/OPEN_SOURCE_REFERENCES.md) and [docs/SOURCES_AND_RECOMMENDED_SOFTWARE.md](docs/SOURCES_AND_RECOMMENDED_SOFTWARE.md).

## Development

### Run Locally

Use Python 3.11 or 3.12 if possible. Some fresh Homebrew Python 3.14 builds can fail
inside `ensurepip`/`pyexpat` on macOS; if that happens, create the venv with a stable
Python executable such as `python3.11`.

Fast path from the repo root:

```bash
./happysmile
```

That script creates `.venv` if needed, installs the editable dev package once,
and starts the local server at `http://127.0.0.1:8000`. You can pass the same
server flags through it:

```bash
./happysmile --host 127.0.0.1 --port 8123
```

The more literal alias works too:

```bash
./run-openortho
```

After an editable install with the virtual environment active, these console
commands are also available:

```bash
openortho
happysmile
orthoplan serve
```

Manual setup remains:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orthoplan serve
```

Then open:

```text
http://127.0.0.1:8000
```

If your shell has a working `python3` but not `python`, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orthoplan serve --host 127.0.0.1 --port 8000
```

If venv creation fails partway through, remove the broken environment and recreate it:

```bash
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orthoplan serve
```

Run tests:

```bash
pytest
cd ui
npm test
cd ..
python3 tools/check_maintainability.py
```

### Local Mesh Workspace

Plan JSON never stores mesh bytes. To render real per-tooth STL meshes locally,
register each STL in a local mesh workspace, then link the returned `id` in the
plan's `mesh_assets` and `tooth_meshes`.

```bash
orthoplan register-mesh path/to/tooth_11.stl --workspace .orthoplan-meshes
ORTHOPLAN_MESH_WORKSPACE=.orthoplan-meshes orthoplan serve
```

The dev server exposes registered meshes only by asset id at `/api/mesh/<mesh_asset_id>`.
The UI renders real linked STL meshes when available and falls back to schematic
proxy teeth when no registered mesh can be loaded.

## Contribute Your Data

Modern clear-aligner planning systems succeed partly because they learn from a
large base of scans, planned setups, refinements, and outcomes. OpenSource Ortho
needs an open, privacy-preserving version of that evidence base. For a general
user, the most helpful contributions are, from most to least useful:

1. **Before-and-after STL scans**: upper and lower scans from before treatment
   and after treatment, ideally from the same scanner/export format.
2. **Progress or refinement scans**: any mid-treatment scan, refinement scan, or
   scan taken when trays stopped tracking.
3. **The intended plan in a non-proprietary form**: an OpenSource Ortho plan JSON,
   a hand-entered summary, or notes listing stage count, wear interval, which
   teeth moved, attachments, IPR/spacing, and any locked teeth.
4. **Outcome notes**: whether refinements were needed, whether trays tracked, what
   changed mid-treatment, scanner model, scan units, and known scan quirks -
   without patient identity.
5. **Initial STL scans only**: still useful for segmentation, scale, mesh-quality,
   and arch-form benchmarks, but they cannot teach outcome prediction by
   themselves.
6. **Optional imaging-derived anatomy**: reviewed CBCT/DICOM-derived root/bone
   records only when you have the right to share them and PHI has been removed.

Privacy is enforced in code, not just requested. The manifest model
(`orthoplan/model/dataset.py`) stores redacted metadata only (never mesh bytes),
reduces filenames to a basename, forbids unknown fields, and has **no** name,
date-of-birth, contact, or record-number fields by construction (locked by a
test). Register a contribution locally to generate a stable `spec-<uuid>` id,
hash each STL, and write the manifest:

```bash
orthoplan register-contribution upper.stl lower.stl \
  --arch maxillary --units mm --i-confirm-no-phi \
  --out datasets/<your-folder>/manifest.json
```

The `--i-confirm-no-phi` flag is required and asserts you have removed
patient-identifying information. For long-term usefulness, put each case in a
folder named by that specimen id and use standard file labels such as
`initial-upper.stl`, `initial-lower.stl`, `final-upper.stl`, `progress-01-upper.stl`,
and `plan-summary.json`. See [docs/DATA_CONTRIBUTION.md](docs/DATA_CONTRIBUTION.md)
for the full case-bundle standard, manifest schema, and privacy rules, and
[docs/SAFETY.md](docs/SAFETY.md) before sharing anything.

New to dental terminology? The [Glossary](docs/GLOSSARY.md) explains key terms
(IPR, tip, torque, crowding, FDI numbering) and includes a tooth-numbering
diagram; it is also reachable in the app via the **Key Terms** sidebar button.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch
and pull-request conventions, the contribution-type tags, the safety rules that
are enforced by code and review, and how to run the same checks CI runs. Commit
history is the canonical record of changes (`git log`).
