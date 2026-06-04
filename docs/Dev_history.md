# Development History

This file tracks status notes intended to be updated alongside commits. Claude Code hooks in `.claude/settings.json` call `tools/update_dev_status.py` after `git commit` commands run inside Claude Code.

## Current Status

- Project scaffold created.
- Safety boundary documented before implementation.
- Core data model, finding vocabulary, and provider interfaces scaffolded.
- Visual progress representation elevated to a primary product requirement.
- Architecture, reference, and movement-cap docs added.
- Maintainability and composability guardrails added.
- First provider adapter target: OpenAI.
- Second provider adapter target: Claude Code.

## Entries

### 2026-06-03 - Scaffold

- Created initial repository structure for OpenSource Ortho.
- Added safety-first README and SAFETY boundary.
- Added development-status automation docs and Claude Code hook scaffold.
- Added optional `.githooks/post-commit` hook for non-Claude commits.
- Set the initial OpenAI provider adapter default to `gpt-5.5`.

### 2026-06-03 - Visualization Priority

- Added `UI_DESIGN.md` to define the visual accuracy and UI design contract.
- Added cumulative stage-frame data structures for future UI viewers.

### 2026-06-03 - Architecture Review

- Added `ARCHITECTURE.md` with the plain-language upload-to-visualization workflow.
- Added `OPEN_SOURCE_REFERENCES.md` to separate permissive open-source dependencies from proprietary workflow references.
- Added configurable `MovementCaps` and a deterministic movement-cap evaluator.
- Improved commit-status hooks so generated dev-history notes are amended into the new commit instead of leaving the tree dirty.

### 2026-06-04 - Maintainability Guardrails

- Added `MAINTAINABILITY.md` to define module ownership, file-size thresholds, and review hygiene.
- Added `tools/check_maintainability.py` for lightweight code-size and structure checks.
- Added a Claude Code hook to run the maintainability check during commit workflows.
- Added OpenAI agent guidance for composable code changes.

### 2026-06-04 - Documentation Organization

- Moved project docs into `docs/` to keep the repository root focused.
- Added `docs/README.md` as the documentation index.
- Added `docs/SOURCES_AND_RECOMMENDED_SOFTWARE.md` as a living source ledger for upstream references, recommended software, and monitoring cadence.

### 2026-06-03T23:41:54+00:00 - Commit Status

- Commit subject: Scaffold safety-first orthodontic planning toolkit
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T00:53:12+00:00 - Commit Status

- Commit subject: Add maintainability guardrails
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T00:57:53+00:00 - Commit Status

- Commit subject: Organize documentation under docs
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T00:58:58+00:00 - Commit Status

- Commit subject: Fix dev history commit status format
- Status: development history hook observed and recorded this commit workflow.
