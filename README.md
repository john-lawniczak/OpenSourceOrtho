# OpenSource Ortho

[![CI](https://github.com/john-lawniczak/OpenSourceOrtho/actions/workflows/ci.yml/badge.svg)](https://github.com/john-lawniczak/OpenSourceOrtho/actions/workflows/ci.yml)

OpenSource Ortho is an open-source orthodontic treatment-planning research toolkit for clear-aligner workflows.

Most project documentation lives in [docs/](docs/README.md).

New users can start with [HOW_TO.md](HOW_TO.md).

The first static UI prototype lives in [ui/](ui/README.md).

It is not an Invisalign clone, medical device, diagnostic system, or treatment approval system. The project focuses on geometric representation, configured-rule checks, staged tooth-movement proposals, visualization, printable package generation, and advisory evaluation under explicitly declared data limitations.

Visual progress representation is a first-class requirement. The UI must accurately show staged tooth movement, data gaps, units, and provenance without implying approval. See [docs/UI_DESIGN.md](docs/UI_DESIGN.md).

## Boundary

The software may:

- represent proposed tooth movements and staged aligner-style plans
- import, export, and visualize dental mesh data
- check internal consistency against user-configured movement caps
- surface observational findings, data gaps, and handoff questions
- rank missing data by deterministic acquisition impact
- run local or remote model providers for advisory review
- generate reproducible handoff reports tying inputs to engine version and findings

The software may not:

- diagnose disease or malocclusion
- decide whether treatment is safe, suitable, approved, or complete
- infer unseen anatomy such as roots, bone, periodontal status, or CBCT findings
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

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the plain-language system overview.

## Maintainability

The project should stay modular and composable as it grows. Follow [docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md) for file-size guardrails, directory ownership, review checklist, and the maintainability check script.

## Initial Build Order

1. Safety and scope docs.
2. Core data model: `TreatmentPlan`, `Stage`, `ToothDelta`, `DataAvailability`.
3. IO and synthetic meshes.
4. Setup and staging engine with configurable caps.
5. Deterministic evaluators.
6. Controlled finding vocabulary.
7. Model provider adapters: OpenAI first, Claude Code second.
8. Prompt boundary injection.
9. Visualization frame contract and UI prototype.
10. CLI glue.

## References

Commercial software such as BlueSkyPlan and ClinCheck may be studied as workflow references only. Do not fork, copy, reverse engineer, or import proprietary source, assets, terminology, or private workflows. See [docs/OPEN_SOURCE_REFERENCES.md](docs/OPEN_SOURCE_REFERENCES.md) and [docs/SOURCES_AND_RECOMMENDED_SOFTWARE.md](docs/SOURCES_AND_RECOMMENDED_SOFTWARE.md).

## Development

### Run Locally

Use Python 3.11 or 3.12 if possible. Some fresh Homebrew Python 3.14 builds can fail
inside `ensurepip`/`pyexpat` on macOS; if that happens, create the venv with a stable
Python executable such as `python3.11`.

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
/Users/johnlaw/.local/bin/python3.11 -m venv .venv
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

## Repository Status

Development history and commit-status notes live in [docs/Dev_history.md](docs/Dev_history.md). Claude Code project hooks are scaffolded under `.claude/` to append a lightweight status entry after `git commit` commands run inside Claude Code. The normal Git `post-commit` hook records the new commit status and amends the just-created commit with that note, guarded against recursion.

For normal Git commits, initialize the repo and opt into the included hook path:

```bash
git init
git config core.hooksPath .githooks
```
