# Mobile scanner import and comparison audit — 2026-09-22

**Ship rating: 8/10 for the research preview.** This is not an app-store readiness
assessment. The subsequently authorized public source snapshot is documented in
the [publication record](PUBLIC_RELEASE_2026-09-22.md).

## Behavior delivered

Both apps (0.4.0, build 4) locally preview STL, OBJ, PLY, ASC, XYZ, and PTS.
USER_ONE opens with both real arches, clearer neutral surface lighting, and a
continuous baseline/week-7 reveal with synchronized rotation and zoom. The four
original dataset STLs remain unchanged and permanently tracked. The renderer
shows complete observed geometry without inventing intermediate tooth movement.
See [supported variants and bounds](../mobile/SCAN_IMPORT.md),
[iOS capture](images/mobile-ios-real-scans.png), and
[Android capture](images/mobile-android-real-scans.png).

## Concrete findings and applied fixes

| Priority | Finding, impact, and exact fix | Evidence |
| --- | --- | --- |
| High | Naive polygon fan triangulation can turn concave or self-intersecting OBJ/PLY faces into incorrect surfaces. `ScanImport.swift` and `ScanImport.kt` now validate planarity and every vertex against every polygon edge before triangulation; reject ambiguous faces and non-unit OBJ homogeneous weights. | Shared concave, star, non-planar, weighted, clockwise, quad, and negative-index fixtures. |
| High | Changing the picker modality from `stl` to `scan` initially bypassed iOS preview loading and could display USER_ONE after an upload. `LiteFlowViewModel`, `PreviewScan`, and both Teeth screens now retain pending/failed surface records, select imports independently of read success, and display failures explicitly. | Code-path review, shared parser failures, and Android picker checks; imported provider race automation is still incomplete. |
| Medium | Extension-only or modality-only STL classification could admit OBJ files into the STL fallback; request metadata also defaulted new formats to STL. Both `LiteFlow` implementations now require a surface modality plus the STL extension for fallback and preserve actual scan extensions in metadata. Both view models stop non-STL surface generation. | Tests check all six extensions, uppercase names, misleading modalities, request format metadata, and fallback eligibility. |
| Medium | iOS read selected file bytes on the UI thread, trusted size metadata, and could retain unbounded uploads. `ScanImportIO` now enforces the byte limit during background reads; iOS limits retained surface files to two, cancels reads on reset, and ignores late results for removed records. Both loaders cancel obsolete parsing and enforce combined vertex budgets. | Bounded-read tests use oversized streams/sparse files; cancellation tests pass. Physical-device stress testing remains necessary. |
| Medium | Import errors were held in state without appearing on either Upload screen. iOS also cleared the importer enum when the picker dismissed before its completion could use it. Upload now displays errors; iOS completion retains the selected import kind. Android metadata-query failures are caught and reported. | Direct callback/state review and Android failed-import check. |
| Medium | ASCII STL used millions of boxed Floats on Android. It now uses `FloatValues` primitive storage; new text readers also cap line length before tokenization. External OBJ material paths are never opened. | Full four-STL regression, overlong-line tests, and OBJ fixture with an external material URL. |
| Medium | Re-parsing scans on slider updates would make dragging expensive. Source identity and arch selection are separate from comparison progress: both visits are loaded once per source, then only the SceneKit mask/OpenGL scissor changes. Android caches shader locations and draws only on interaction. | iOS UI endpoint/midpoint checks and Android manual reveal/rotation checks. No frame-rate benchmark is claimed. |
| Medium | A week-7 view could still display baseline triangle counts, and near-end slider values could leave a thin unintended reveal. Counts now follow the complete endpoint, mixed-view counts are explicitly labeled Baseline, and the final 1% snaps to exact endpoints. | iOS UI checks all four exact face counts; Android endpoint verification. |
| Medium | GL shader/allocation failures could escape the render thread as an app crash. `ScanRenderer` now reports initialization failures back to the screen and suppresses further draws on failure. Context recreation rebuilds buffers. | Successful emulator rendering; device-specific GPU failures were not fault-injected. |
| Medium | The preceding private Android CI run failed before compilation because setup requested the removed SDK `tools` package. `.github/workflows/mobile.yml` now explicitly requests platform-tools, API 34, and build-tools 34.0.0. | The previous development run failed at SDK setup; both native jobs passed after the fix. |

No provider/model behavior changed. The implementation audit did not change dataset originals or consent scope.
The later publication authorization and exclusions are recorded separately. Source/renderer/parser modules
remain below the repository thresholds; the two legacy screen files did not grow.

## Verification

- Swift: 19 tests pass, including 38 shared scanner cases, exact original face
  counts, bounded reads, cancellation, and metadata/fallback classification.
- Android: 19 JVM tests pass over the same cases; debug build and lint pass
  (0 errors, 12 existing warnings for SDK/dependency currency, icons/tooling,
  and allocations in the schematic tooth map).
- iOS simulator: build and automated UI test pass for both arches, midpoint
  reveal, baseline/week-7 endpoints, single-arch selection, and reset.
- Android Pixel 9 emulator: real surfaces, reveal, and rotation checked visually;
  synthetic binary PLY and malformed PLY exercised through the document picker.
- Python: 668 pass, 2 optional-backend skips. The sandbox initially blocked 28
  localhost-server tests; all 28 passed when rerun with local-server permission.
- JavaScript: 124 pass. Browser end-to-end tests were not rerun for this native
  change (the preceding release review records their prior run).
- Ruff, generated dataset catalog, strict maintainability, and Git whitespace
  checks pass. Sample loader hashes and exact-face regression tests preserve all
  four original surfaces.

## Top remaining risks

1. **Unregistered observations.** Independent fitting is useful for visual review
   but cannot establish a tooth displacement or an upper/lower bite. The UI and
   documentation explicitly identify the reveal as two observations. The week-7
   milestone is contributor-confirmed, not computed from export-date spacing.
2. **Physical-device resource limits.** Four complete scans retain approximately
   87 MB of interleaved CPU geometry plus GPU/copy overhead. One Android emulator
   observation was about 306 MiB total PSS (373 MiB RSS); this is not a device
   budget or peak guarantee. Low-memory phones, thermal behavior, and rapid source
   switching across different GPUs still need sustained profiling.
3. **Importer/provider breadth.** Native parsers cover documented subsets and
   synthetic fixtures, not a hardware-vendor certification suite. Actual exported
   POP 3/Fox files, cloud-provider delays/revoked access, process recreation, and
   repeated reset/import races need broader automated coverage. Textures, scanner
   project archives, durable storage, and byte registration with the engine remain
   outside this release.

## Three highest-leverage follow-ups

1. Establish verified units and reviewed cross-time/bite registration before
   adding displacement measurements or per-tooth animation.
2. Profile physical iOS and Android devices; adopt indexed geometry and a bounded
   decoded-mesh cache if measured memory/latency justify them.
3. Add consented vendor-export fixtures and automated document-provider/lifecycle
   tests on both platforms, including denied reads and rapid reset/source changes.
