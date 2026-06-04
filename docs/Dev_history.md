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

### 2026-06-04 - Print Export, How-To, and LLM Review Guidance

- Added `PrintExportSettings` to the treatment settings model and `orthoplan.printing` readiness output for user-directed model printing/thermoforming handoff metadata.
- Exposed `print_export` in API evaluation output and the UI review panel; the UI now includes print-export settings and a first-user Getting Started panel.
- Added root `HOW_TO.md` with workflow, printing/material boundaries, and commands, plus `docs/LLM_PROMPTS.md` with safety-framed optional LLM review prompts.
- Updated architecture and safety docs for print/manufacturing boundaries and optional parallel LLM/sub-agent review.
- Added print export tests and regenerated synthetic example plans for the expanded settings schema.

### 2026-06-04 - Measurement Truth + Acquisition Advisor Sequence

- Expanded Measurement Truth Lab coverage with file-backed synthetic STL bounds checks, PCA tolerance checks, and property-style cumulative transform tests.
- Implemented `orthoplan/evaluation/acquisition.py`: deterministic counterfactual acquisition advice that reruns `run_rules`, diffs findings/data gaps, ranks marginal impact, and stays verdict-free.
- Added `orthoplan acquisition`, embedded `acquisition_advice` in API output, and rendered an "Acquire Next" UI panel from backend output only.
- Added optional reviewer metadata and HMAC-SHA256 signatures to handoff reports.
- Expanded e2e coverage to check acquisition panel rendering, 2D canvas pixels, and API rejection states when Playwright is available.

### 2026-06-04 - Phase 8: Trust and Measurement Readiness

- Downgraded approximate PCA tooth frames: they remain exposed as metadata, but no longer make rotation renderable. Rotation rendering now requires a non-approximate trusted anatomical frame or a globally resolved anatomical coordinate frame.
- Added structured `data_gap_actions` to the evaluation API so missing data carries impact, next step, and blocked-capability fields instead of only passive gap strings. The UI sidebar now renders these actions.
- Added `orthoplan/reporting.py` and `orthoplan report`: deterministic handoff JSON with engine version, canonical plan hash, stable evaluation hash, input metadata, evaluated findings, data-gap actions, progress frames, and report hash.
- Added measurement-readiness golden tests for cumulative translation and movement-cap math, plus table-driven safety invariant tests that reject verdict language across every text field.
- Updated safety, architecture, UI, walkthrough, and README docs to match the stricter visualization and handoff contracts.

### 2026-06-04 - Post-Implementation Audit: Provider/CLI Hardening

- Reviewed the recent Phase 4/5/6/7 implementation set with a merge-readiness focus.
- Fixed local test collection for bare `pytest` by adding the repo root to pytest's configured `pythonpath`.
- Hardened `plan-summary` and `advise` so malformed plan files return clean CLI errors instead of tracebacks.
- Hardened OpenAI and Claude Code provider adapters so SDK/subprocess failures are converted into `RuntimeError` for the advisory CLI boundary.
- Added regression tests for malformed CLI plan input and provider failure normalization.

### 2026-06-04 - Phase 5: Model Advisory Layer

- Added `orthoplan/evaluation/advisory.py`: a strict `AdvisoryItem`/`AdvisoryResponse` schema, `parse_advisory` (tolerates markdown fences), and `request_advisory(plan, provider)` that converts model output to `Finding(provenance=MODEL)` and runs it through `quarantine_findings` (the same `lint_finding` gate). Parse failures and lint rejections are returned as data (`AdvisoryResult.parse_error` / `.rejected`); it never raises on bad model output.
- `prompt.build_advisory_request` injects the safety boundary, declared `DataAvailability`, configured `MovementCaps`, and the JSON output schema; the model is told not to use verdict words or the `mechanics` category, with the lint gate as defense-in-depth.
- Added the opt-in `orthoplan advise` CLI command (clean error without a provider/key). The default `api.evaluate_plan` never calls a model.
- Added `tests/test_advisory.py` (valid, verdict, model-mechanics, warning-missing-fields, invalid JSON, schema mismatch, fenced, mixed batch). Accepted advisories always render with the `[ADVISORY - unverified]` prefix. Updated `docs/OpenAI_Agents.md` and the CLI walkthrough.
- 92 Python tests + 11 JS tests pass; maintainability passes. Phase 5 exit criteria met.

### 2026-06-04 - Phase 4 Rules + Phase 7 CLI Walkthrough & Screenshots

- Phase 4 deterministic rules (`evaluation/rules/plan_checks.py`, registered in `engine.run_rules`): `evaluate_root_sensitive_movement` (WARNING when tip/torque/intrusion is planned without roots or CBCT), `evaluate_segmentation_presence` (NOTICE when movement is planned with no per-tooth segmentation), and `evaluate_no_movement` (INFO when stages have only zero deltas). Other planned checks (stage contiguity, duplicate tooth, mixed numbering/frame) are already enforced at the model layer; timeline outliers deferred (needs a cited band, not an invented threshold). Added `tests/test_plan_checks.py`.
- `plan-summary` now labels output "Findings:" (it lists all rule findings, not just caps).
- Phase 7: `docs/CLI_WALKTHROUGH.md` with real command output; `tools/capture_screenshots.py` (Playwright) regenerates `docs/images/stage-builder.png` and `review-3d.png` headlessly with no patient data; screenshots embedded in `ui/README.md`. Tightened the 3D viewer camera/grid so proxies read better.
- 83 Python tests + 11 JS tests pass; maintainability passes. Phase 7 readiness items complete.

### 2026-06-04 - Phase 7: Examples, Contribution Guide, License Audit

- Added synthetic example plans under `examples/`: a generator (`generate_examples.py`, fixed timestamp for stable output) plus checked-in `basic_plan.json` (trips the linear cap) and `segmented_plan.json` (per-tooth approximate frame; later Phase 8 changed this to non-renderable rotation). `tests/test_examples.py` asserts they load, evaluate, and stay in sync with the generator.
- Added `CONTRIBUTING.md`: setup, the exact CI checks, the non-negotiable safety rules (no patient data, no verdict language, deterministic rules own mechanics, geometry-not-biomechanics, UI never reimplements the engine), module ownership table, and dependency policy.
- Added `docs/LICENSE_AUDIT.md`: per-dependency licenses verified from installed metadata/PyPI (all permissive: MIT/BSD/Apache-2.0/PSF; no copyleft), including the vendored Three.js (MIT) and the build-only Chromium. Linked from the docs index.

### 2026-06-04 - Phase 7: CI + Headless Viewer Smoke

- Added `.github/workflows/ci.yml` with three jobs that gate every push and PR: Python (`pytest -q` + maintainability `--strict`, Python 3.12), JS (`node --test` in `ui/`), and an e2e Playwright job.
- Added `tests/e2e/test_viewer_smoke.py`: loads the dev server in headless Chromium and asserts the Three.js viewer mounts a sized WebGL canvas with no uncaught page errors. Skips cleanly when Playwright is absent, so the default `pytest` stays green (`70 passed, 1 skipped`).
- Verified for real in a clean Python 3.11 venv: editable install + the full suite, and the Playwright smoke actually passed in headless Chromium (closing the prior "render not browser-verified" caveat).
- Fixed packaging: added `[tool.hatch.build.targets.wheel] packages = ["orthoplan"]` so `pip install -e .` resolves the package (previously unset). Added the `e2e` optional dependency (`playwright`).

### 2026-06-04 - Phase 6: Three.js 3D Progress Viewer

- Added `ui/viewer3d.js`: a Three.js scene rendering abstract per-tooth proxies from the engine's `frames[].poses[]`, with orbit controls, current/planned/overlay modes, a stage scrubber, displacement vectors, and a movement-exaggeration control. No scanned mesh bytes are served, so proxies (not real geometry) are rendered by design.
- Rotation was initially drawn where the engine set `rotation_renderable`, oriented by the approximate per-tooth PCA frame exposed as `tooth_frames` in `/api/evaluate`. Phase 8 superseded this: PCA frames remain metadata only and no longer authorize rendered rotation.
- Three.js r169 (MIT) and OrbitControls are vendored under `ui/vendor/` and loaded via an import map, so the app runs offline with no runtime external calls.
- Added pure helpers to `ui/core.js` (`degToRad`, `displacement`, `rotationApplications`) with Node tests, and `tooth_frames` API tests. Added a 2D fallback when WebGL is unavailable. 70 Python + 11 JS tests; maintainability passes.
- Not yet automated: headless-browser rendering verification (wiring verified via Node import of Three + served-asset checks).

### 2026-06-04 - Risk Burndown: JS Tests, Contract Parity, Approximate Rotation Frame

- Contract parity: added `ui_dict()` to `ToothPose`/`StageProgressFrame` derived from `model_dump` so the UI frame contract can never silently drop a model field; `api.py` uses it; added parity tests asserting `ui_dict` keys == model fields.
- JS unit tests: extracted DOM-free logic to `ui/core.js` (HTML escaping, contiguous stage reindex, frame pose extraction, async stale-response token guard); `render.js`/`plan.js` now import it; added `ui/core.test.js` (8 tests, `node --test`) and `ui/package.json` (`type: module`).
- Rotation rendering (original decision, superseded by Phase 8): added `ToothLocalFrame` (geometry) and `planning/mesh_frame.py` (pure-Python Jacobi PCA, returns None for degenerate clouds); `read_stl_geometry` exposes vertices in one read; `import_segmented_meshes` attaches an approximate frame per tooth. Phase 8 changed PCA frames to metadata-only, so they no longer flip `rotation_renderable`.
- 68 Python tests + 8 JS tests; maintainability passes. Updated SAFETY, plan, and this log.

### 2026-06-03 - Audit Fixes: Dev Server Hardening and UI Race

- Dev server: malformed `Content-Length` now returns a clean 400 instead of dropping the connection; empty body is 400 (was 413); `do_GET`/`do_POST` are wrapped so an unexpected error returns a 500 JSON instead of a reset/traceback; added a 30s request timeout so a client that declares but never sends a body cannot hang a worker thread.
- UI: added a monotonic request token to `runEvaluate` so a slow in-flight `/api/evaluate` response can no longer overwrite a newer one (stale-render race).
- Added `tests/test_server.py` (index serving, path-traversal 404, valid evaluate, invalid-JSON/empty-body/malformed-Content-Length 400, oversized 413, unknown-endpoint 404). 61 tests; maintainability passes.

### 2026-06-03 - Phase 3 Mesh Validation and Segmentation Import

- Added `evaluation/rules/mesh_quality.py`: deterministic, lint-passed NOTICE findings for degenerate triangles, non-watertight/inconsistent-winding meshes, and confirmed-but-implausible scale.
- Added `evaluation/engine.run_rules()` as the single deterministic-rule aggregator; api and CLI now run the full rule set (movement caps + mesh quality) through it.
- Added `segmentation/imports.import_segmented_meshes()`: inspect one STL per tooth and return plan-ready mesh assets + tooth links, rejecting two teeth that resolve to identical mesh content.
- Added tests for mesh-quality findings and segmentation import (53 tests; maintainability passes).
- Documented the open decision that a per-tooth local frame (needed to flip `rotation_renderable`) requires a safety-framed estimation method before implementation.

### 2026-06-03 - Wire UI to the Python Engine

- Added `orthoplan/api.py` (`evaluate_plan`/`evaluate_plan_payload`): the single, pure, never-raising evaluation entry point returning lint-gated findings, data gaps, the timeline projection, and `StageProgressFrame` data; validation errors are returned as data.
- Added `orthoplan/server.py`, a localhost stdlib dev server that serves `ui/` and exposes `POST /api/evaluate` (binds 127.0.0.1, caps body size, refuses path traversal), plus an `orthoplan serve` CLI subcommand.
- Rewired the UI to consume the engine: removed the JavaScript reimplementations of findings/data-gaps/cumulative poses; the canvas now renders the engine's frames, findings show their data gap and follow-up question, and an "engine offline" state replaces any silent fallback.
- Added `tests/test_api.py` (valid output, safety fields, invalid-FDI and non-contiguous-stage errors, scale gate). 46 tests; maintainability passes.

### 2026-06-03 - Post-Implementation Audit Fixes

- Hardened mesh-linkage validation: a `ToothDelta` may now only reference the mesh segmented to its OWN tooth (prevents moving another tooth's geometry), and duplicate mesh asset ids across scans/mesh_assets are rejected.
- UI prototype: escaped all dynamic `innerHTML` injection (file name, tooth, gaps, findings) to close an XSS vector; reindexed exported stages to contiguous 0..n-1 so UI output always satisfies the Python plan contract; hardened numeric inputs against `NaN`.
- UI prototype: added safety caveats by the viewer (translation-only, rotation not rendered, crown-centroid pivot is a visualization assumption) and by Findings (observational, interpret against listed data gaps).
- Added regression tests for wrong-tooth mesh references and duplicate asset ids (41 tests; maintainability passes).

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

### 2026-06-03 - Phase 1 Data-Model Core

- Replaced free-form `coordinate_frame` strings with a typed `CoordinateFrame` (`model/geometry.py`); `z` is occlusogingival, tip/torque/rotation flagged non-renderable when anatomical axes are unavailable.
- Made `ToothId` canonical FDI with validation; derived `arch` from the FDI quadrant and dropped the redundant stored `arch`; plan creation rejects mixed numbering systems and mixed frames.
- Moved cumulative pose composition into `planning/transforms.py` (crown-centroid pivot, true translation vector sum, rotation reported but `rotation_renderable=False`); `viz/progress.py` now consumes it instead of computing it.
- Centralized data-gap text in `model/gaps.py` (was duplicated between viz and the cap rule).
- Reworked `MovementCaps` into `AxisCaps` (`default` + reserved `per_tooth_overrides`); cap rule now uses Euclidean horizontal magnitude, a separate vertical cap, and is gated on confirmed scan units.
- Added `model/assets.py` (`MeshAsset`/`UploadedScan`, `MeshUnits` defaulting to `unverified`, redacted relative references, absolute-path rejection) and metadata-only `io/stl_import.py` (no mesh bytes stored).
- Consolidated the safety gate into `lint_finding()`: verdict scan across all text fields with word-boundary matching, model-sourced `mechanics` findings forbidden, and `quarantine_findings()` so invalid model output is rejected, not crashed. Construction is no longer the gate.
- Added arithmetic `planning/timeline.py` (inputs only, computed duration, standing caveat), JSON serialization helpers (`io/serialization.py`), and CLI subcommands `new-plan`, `inspect-stl`, `plan-summary`.
- Updated ARCHITECTURE, SAFETY (geometry-not-biomechanics + privacy posture), MAINTAINABILITY, OpenAI_Agents, and references docs to match. Tests expanded to 26; maintainability check passes.

### 2026-06-04 - Next Context Plan

- Added `docs/NEXT_CONTEXT_IMPLEMENTATION_PLAN.md` as the phased implementation handoff for the next coding context.
- Prioritized the next iteration around the full data-model workflow: STL upload, uploaded scan metadata, treatment plan, timeline estimate, stages, tooth deltas, data availability, movement caps, and UI controls.

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

### 2026-06-04T01:01:28+00:00 - Commit Status

- Commit subject: Add phased implementation plan
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04 - Phase 1 Data Model Review

- Reviewed the Phase 1 data-model workflow changes before merge.
- Added regression coverage for malformed STL uploads, CLI error handling, shared scan-unit data gaps, and movement-cap override validation.
- Hardened metadata-only STL inspection against oversized files and inconsistent ASCII facet/vertex data.

### 2026-06-04 - Phase 2 UI Prototype

- Added explicit segmented tooth-to-mesh linkage for manual/imported segmentation workflows.
- Added mesh quality reporting with internal STL checks and optional `trimesh` support.
- Added a static Phase 2 UI prototype under `ui/` for STL upload metadata, data availability, movement caps, stage entry, timeline projection, findings, and progress preview.

### 2026-06-04T01:32:42+00:00 - Commit Status

- Commit subject: Implement Phase 1 data model workflow
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T01:44:40+00:00 - Commit Status

- Commit subject: Add Phase 2 UI prototype and mesh linkage
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T02:22:30+00:00 - Commit Status

- Commit subject: Audit fixes: mesh-link integrity, UI XSS/contract hardening
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T02:23:32+00:00 - Commit Status

- Commit subject: Audit fixes: mesh-link integrity, UI XSS/contract hardening
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:02:23+00:00 - Commit Status

- Commit subject: Wire UI to Python engine via api.py + dev server
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:03:02+00:00 - Commit Status

- Commit subject: Wire UI to Python engine via api.py + dev server
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:07:09+00:00 - Commit Status

- Commit subject: Phase 3: mesh-quality findings rule + segmentation import
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:07:09+00:00 - Commit Status

- Commit subject: Phase 3: mesh-quality findings rule + segmentation import
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:15:35+00:00 - Commit Status

- Commit subject: Harden dev server and fix UI evaluation race
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T03:16:23+00:00 - Commit Status

- Commit subject: Harden dev server and fix UI evaluation race
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04 - Commit Status

- Commit subject: Burn down top risks: JS tests, contract parity, approximate rotation frame
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T19:45:47+00:00 - Commit Status

- Commit subject: Burn down top risks: JS tests, contract parity, approximate rotation frame
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04 - Commit Status

- Commit subject: Phase 6: Three.js 3D progress viewer
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T19:59:24+00:00 - Commit Status

- Commit subject: Phase 6: Three.js 3D progress viewer
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:06:34+00:00 - Commit Status

- Commit subject: Phase 7: CI + headless 3D-viewer smoke test
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:06:34+00:00 - Commit Status

- Commit subject: Phase 7: CI + headless 3D-viewer smoke test
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:13:39+00:00 - Commit Status

- Commit subject: Phase 7 readiness: example plans, contribution guide, license audit
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:13:39+00:00 - Commit Status

- Commit subject: Phase 7 readiness: example plans, contribution guide, license audit
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:23:20+00:00 - Commit Status

- Commit subject: Phase 4 deterministic rules + Phase 7 CLI walkthrough & screenshots
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:23:20+00:00 - Commit Status

- Commit subject: Phase 4 deterministic rules + Phase 7 CLI walkthrough & screenshots
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:33:07+00:00 - Commit Status

- Commit subject: Phase 5: model advisory layer
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:33:07+00:00 - Commit Status

- Commit subject: Phase 5: model advisory layer
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:38:10+00:00 - Commit Status

- Commit subject: Audit harden advisory CLI and providers
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:41:22+00:00 - Commit Status

- Commit subject: Add Acquisition Advisor implementation plan
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:41:23+00:00 - Commit Status

- Commit subject: Add Acquisition Advisor implementation plan
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:48:32+00:00 - Commit Status

- Commit subject: Phase 8 trust and measurement readiness
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T20:58:38+00:00 - Commit Status

- Commit subject: Add acquisition advisor and measurement truth coverage
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T21:05:30+00:00 - Commit Status

- Commit subject: Add print export readiness and user guidance
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T21:13:35+00:00 - Commit Status

- Commit subject: Document measurement lab and next readiness work
- Status: development history hook observed and recorded this commit workflow.

### 2026-06-04T21:29:50+00:00 - Commit Status

- Commit subject: Add trust and measurement readiness features
- Status: development history hook observed and recorded this commit workflow.
