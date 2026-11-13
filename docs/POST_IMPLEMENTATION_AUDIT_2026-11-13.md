# November 13 post-implementation audit

Scope: all 13 commits dated November 13 through `ed6ad67`, starting at
`a48babd` (comparison base `a48babd^`), plus the fixes described below.
This covers plan discussion notes, highlighted teeth, guided navigation,
assistant settings entry, observed weeks, week 18 capture identity and seed
labels, surface repair/cleanup, the private cleanup archive, and the first
retainer-reference step. Changed code and adjacent persistence, rendering,
server and geometry contracts were reviewed. This is a software review of the
research toolkit, not verification of tooth anatomy or physical-use readiness.

## Findings and fixes

| Severity | Problem and impact | Applied fix and evidence |
| --- | --- | --- |
| P1 | File imports checked unsaved work before asynchronous reading, but did not check edits made during the read/hash/storage lookup. A slow import could silently discard newer painting or notes. Two overlapping repair imports could also finish out of order. | `region_review_save.js` exposes a revision check; scan, label, saved-session and repair imports check it before replacement. Repair imports additionally reject superseded requests. Deterministically delayed file reads exercise notes preservation for all three file types and newer-import precedence. |
| P2 | Entering guided details overwrote the sample's remembered view with simulation. Returning to section 2 therefore lost the weekly overview; disposing history also lost its week and camera. | `sample_view.js` derives the effective view without changing the preference. `sample_comparison.js` retains the history viewer until sample exit. Browser tests retain the same canvas, week, highlight preference and rendered camera across sections. Automatic chat context follows the effective view. Fixed in `ed6ad67`. |
| P2 | The Scan history button only navigated out of Details. In Review, Preview and Print it changed the preference but the effective view remained simulation, so clicking appeared to do nothing. | Selecting Scan history returns to section 2 from every guided section that requires simulation. Browser regression covers Review, Preview and Print, preserving the selected week. |
| P2 | Repair bundle import discarded `absentTeeth` and declared units. Reopening an edited USER_ONE scan could enable teeth reported removed and lose scale metadata. Label-only replacement also lost the editing model's absent-tooth guard. | Validate and restore optional absent-tooth and units metadata, including the STL/browser-restore path, and retain the guard after label import. Round-trip tests preserve all four reported absent wisdom teeth and unverified units, reject invalid metadata, and refuse painting an absent tooth. Legacy bundles without these fields remain supported; missing metadata cannot be recovered automatically. |
| P2 | Cancelling a scan request while switching views could raise BrokenPipeError or ConnectionResetError. The general exception handler then attempted a second response on the closed socket, producing another traceback and misleading server-error noise. | Treat those disconnects as a finished GET. Regression tests simulate each disconnect during the response body and assert that no second response is sent. This pre-existing adjacent server bug was reproduced during the broad browser run. |
| P3 | Every painting/retainer viewer eagerly allocated a face-ID selection buffer, even when only rotating or viewing. At 500,000 faces this is roughly 6 MB of extra CPU data before any trim, plus later GPU resources. | Build selection geometry/material/target only on the first trim selection. Existing visible-speck and occluded-face browser tests exercise the lazy path. No broad renderer rewrite. |
| P3 | An invalid optional retainer date such as month 13 threw a raw date-conversion error rather than the input validation message. | Check date validity before ISO conversion; retain calendar round-trip validation. Unit regression covers malformed and impossible dates. |
| P3 | Older tests required the previous teal fill and Tooth Map landing page. They also relied on Details silently changing section 2's view. These expectations no longer matched the requested UI. | Assert the estimated fill and selected indicator, then disable highlighting and verify the normal selected fill. Expect the profile home and explicitly choose individual-tooth exploration before testing its controls. No product default or color change was needed. |

## Other checks

- Trimming selects actual visible triangle IDs, including small specks whose
  brush center lies over empty space. Depth testing protects occluded surfaces.
  Removing painted regions requires an explicit override, deleting the whole
  scan is rejected, and retained face bytes/labels remain ordered. Undo and
  save/reopen behavior are exercised by browser and geometry tests.
- Hole fills remain bounded local estimates. The rim and adjoining triangles
  supply the curvature fit; preview acceptance is separate from painting.
  Intersection/topology checks, estimated face ranges and complete repair
  bundles prevent a fill from silently becoming an original observation.
- The cleaned upper is a separately hashed derivative. Seed labels and the
  contributor's later lower cleanup remain unreviewed private artifacts.
  The lower cleanup audit retains the warning about 28 removed faces carrying
  draft label 43; it is not substituted into observed scan history.
- Retainer preparation outputs the exact uploaded STL bytes and an independent
  metadata record with zero proposed movements, zero stages and no wearable
  output. Input changes invalidate a prepared result. Existing movement plans
  and sample state are not inherited or modified.
- Notes and tooth tags use text rendering and remain separate from proposed
  movements and provider requests. The new API-key shortcut reuses existing
  page-only settings and sharing controls. Private asset serving/public-release
  exclusions and source identity checks remain covered by the backend suite.

## Remaining risks and ship assessment

**Ship rating: 8/10 for the private research-toolkit workflow.**

1. A local fill can pass the implemented checks without recovering the true
   tooth shape or proving whole-mesh validity. Open/ambiguous margins and closed
   dents remain unsupported. The trimmed label-43 margin still needs inspection.
2. Dense scanning, brush color updates and some geometry work still consume
   main-thread time and significant memory. Automated coverage does not establish
   performance across low-memory devices or all scanner orientations.
3. Browser saves can be evicted or cleared. Surface undo keeps five versions in
   the current session; the retainer draft lasts only until page reload. Portable
   repair bundles and reference records must be downloaded for durable backup.
4. Weeks 8–17 remain unfitted, with no completed week 1–18 motion simulation.
   Live provider credentials and optional native dependencies were not all tested.

## Three highest-leverage follow-ups

1. Add versioned workspace backup/restore that packages the scan, labels, notes,
   estimated/trimmed provenance and reference-preparation record together.
2. Add independent whole-mesh validation and adverse geometry fixtures for thin
   opposing walls, self-intersections, degenerate triangles and damaged margins;
   show unresolved issues next to each accepted estimate.
3. Measure frame latency and peak memory on the real week 18 pair, then move the
   expensive brush/geometry stages off the main thread or update only changed
   faces. Establish device-specific budgets before extending reconstruction.

## Validation

- JavaScript: **208 passed** on the final implementation.
- Backend: **838 passed, 11 optional-dependency skips** in the broad run;
  **31 passed** in the final server/notes run, including two new disconnect tests.
- Chromium: the full **100-case** run produced **98 passes** and the two stale
  expectations documented above. Both were corrected and passed on targeted
  reruns; no browser failure remains unresolved. A final six-case run covered
  import races, history navigation, retainer export and corrected week colors;
  workspace tests also passed after selecting the intended view explicitly.
- The earlier **11-case** targeted run passed import races, sample return,
  trimming, visible-speck selection, hidden-face protection and real curved-fill
  persistence. Desktop/mobile rendered coverage is included in these tests.
- Ruff, strict maintainability and whitespace checks passed.

The entire browser suite was not rerun after correcting its two obsolete
expectations; affected tests were rerun instead. Browser tests use the existing
local Playwright harness because the in-app browser bootstrap was unavailable.
