# Tool improvement phases

This work addresses the tools rated below 7/10 in the November 11 review.
Ratings are engineering judgments; implementation tests do not establish
patient-specific accuracy. A 6/10 research tool should execute its intended
workflow, preserve provenance, expose failures, and have meaningful independent
known-geometry tests. Real anatomical performance remains a separate criterion.

## Phase 1 — surface segmentation and learned adapters

Added an optional seeded surface-graph segmenter to the two-visit workflow.
Shared-edge connectivity and curvature-weighted paths refine the hybrid regions;
faces disconnected from seeds remain context. This is an experimental candidate,
not a claim of improved real anatomical boundaries. Existing hybrid output stays
the default pending reviewed comparisons. `tools/compare_local_segmenters.py`
compares hybrid, graph, and an installed active model on the same labeled corpus.

The learned adapter now requires a `.onnx.json` sidecar with a model hash,
feature contract, tensor names/layouts, class-to-FDI mapping, arch support,
provenance, and license. It validates actual runtime outputs and rejects shape,
nonfinite, or label-count mismatches. A synthetic ONNX fixture exercises the real
runtime; it is not a trained dental model. Face-order run smoothing has been
replaced by shared-edge island repair, which is invariant to STL face order.

The feature contract is `raw-vertices-normal-centered-centroid-15-v1`; supported
layouts are NFC/NCF inputs and NFL/NLF outputs. Existing arbitrary dental weights
are not automatically compatible. Third-party model weights were not bundled or
claimed validated. A real trained-model comparison still needs a compatible
model and independent reviewed cases.

## Phase 2 — correction round trips and recoverable cases

The two-visit page opens either endpoint directly in the correction editor with
its exact scan bytes, display orientation, and draft labels. Returning edits
checks scan identity before applying them and invalidates the old fit. Both
visits can be relabeled and regenerated without manual JSON transfers.

Portable `.orthocase` backups include original scans, fitted results, corrections,
units, orientation, timing, and selected segmentation backend. Restore verifies
both SHA-256 values, geometry/fit binding, arch, units, and correction contracts.
Imports preserve existing named cases by creating a unique import name. Source
bytes remain local; backups are user-created files and are not uploaded remotely.

Browser tests edit both endpoint labels, refit, save, export, restore in a new
case, and reject a corrupted scan hash while preserving the previous case.

Endpoint match review now accepts an explicit one-to-one map, including holds,
against independent target regions. Duplicate, unknown, and partial maps are
rejected. Reverse-fit cycle error and resampling pose differences are recorded
per tooth and flag unstable fits. These diagnostics are empirical consistency,
not calibrated confidence intervals. Benchmark reports now include per-region
IoU/precision/recall, false-positive context faces, missed faces, and fit coverage;
real-data review flags must be actual booleans, not truthy strings.

## Phase 3 — full-surface checks, bite review, and shell QA

Two-visit cases can inspect full-triangle separation for a selected pair at its
fitted weekly pose. Bounding-volume pruning preserves every triangle; a time or
pair-test budget returns indeterminate, never a clearance claim. This detects
crossings between triangle interiors that vertex samples miss. The sampled
multi-week overview remains available as the inexpensive first pass.

The same bounded kernel now adds inner/outer full-surface separation to shell QA.
Incomplete checks and sub-feature separation downgrade the manufacturing report.
Vertex spacing remains separately reported. Surface separation does not prove
physical fit or rule out containment of closed objects.

`/bite-review.html` displays both original scans without separate recentering.
Users may inspect geometric inference or import a reviewed rigid transform bound
to both source hashes, reviewer, and reference description. Supplied frames are
measured without automatically moving arches into contact. Imported transforms
are not painted as overlays on untransformed geometry. Templates export with
acceptance false. Unit confirmation is required for reviewed-transform imports.

The paired-upload browser test exposed lost registry entries during concurrent
uploads. Registry updates now lock the read/modify/write transaction across
threads and processes; a parallel-upload regression confirms all assets survive.

## Phase 4 — usable local CBCT review and patient-space anatomy proposals

Added streaming regular-series DICOM pixel decoding, geometry checks, rescaling,
and a hash-checked local review packet. A three-plane browser viewer supports
windowing, explicit seed/threshold/ROI growth, overlays, undo, and draft mask
export for the existing anatomy workflow. It rejects overlapping root proposals
and truncated exports. Patient origin/direction are preserved during anatomy
conversion; draft centerlines no longer assume scanner-Z orientation.

Paired landmark registration verifies source bindings and provides held-out
residuals without automatically accepting the transform. USER_ONE's actual
compressed volume was decoded and displayed locally. Reviewed anatomy and a
correct study-to-STL correspondence are still human review inputs. See
[local CBCT review](LOCAL_CBCT_REVIEW.md) for commands, contracts, and limitations.

## Phase 5 — evidence-bound help and reproducible stress benchmarks

The two-visit page now explains its fit through a deterministic local helper.
It ranks held/weak regions for correction, ties each statement to fit evidence,
and distinguishes no estimate from no movement. The endpoint validates bounded
numeric metadata, ignores supplied prose, and lints every educational finding.
No raw scans, pixels or external model calls are involved.

`tools/run_motion_stress.py` records 36 synthetic fitting cases with known
identity: exact repeats, noisy repeats, independent resampling, known rigid
motion, partial surfaces and noisy motion. Exact motion is recovered numerically;
independent resampling produces false motion in 2/6 cases at the declared
0.05 synthetic-mm / 1-degree thresholds. Mean rotation error for that group is
0.915 degrees, maximum 1.759 degrees. This is useful failure evidence, not a
patient accuracy estimate. The committed [report](benchmarks/motion-stress-2026-11-11.json)
includes all cases, thresholds, cycle checks and sampling differences.

Boundary benchmark regression checks now catch context leakage despite perfect
crown-only accuracy, and refuse truthy-string review flags. Missing fits reduce
coverage rather than receiving zero error. Real anatomical accuracy remains null
until independently reviewed labels, poses and repeated real scans are supplied.

## Phase 6 — registration import and downstream frame consistency

Review found that root-aware pivots and root proximity could mix CBCT and STL
coordinates. Root/axis pairs now resolve through their own quality-gated rigid
registration; pivots return to scan space and translations rotate into the CBCT
frame. Reflected/scaled/nonfinite transforms and mismatched study references are
excluded. Root proximity explicitly describes centerline, translation-only
geometry instead of implying a full rotated root-surface check.

The main workspace imports source-bound landmark reports, preserving their
actual transform and held-out metrics. Patient-space masks cannot silently use
the legacy identity transform. Acceptance stays explicit; source IDs, hashes,
units and the volume digest are checked before unreviewed anatomy is generated.
Rotated/translated reference geometry and mismatched-source tests cover these
paths. The synthetic volume benchmark's declared dimensions were corrected to
enclose its root voxels; the new mask validator exposed that old fixture error.

## Phase 7 — refreshed sample evidence and continuous regression coverage

Regenerated both USER_ONE endpoint previews with reverse-cycle and resampling
metrics, preserving the original endpoint hashes and unreviewed status. No week
18 molds or local CBCT pixels entered the public asset catalog. CI now runs on
private development branch patterns and exercises the actual ONNX contract,
imaging adapters, topology, contact and stress tests with their optional stacks.
The learned extra includes its topology dependency; an unconfigured model no
longer imports ONNX Runtime just to fall back to hybrid segmentation, and actual
model sessions disable runtime telemetry.

Existing fixture-import lint annotations and planning-demo browser selectors
were corrected so the full lint/browser checks can run against the current UI.
See [the scorecard](TOOL_SCORECARD.md) for scope-specific reassessment rather than
an unsupported claim of measured anatomical accuracy.

Final local validation: full Python/browser suite **804 passed, 8 skipped**;
additional registration-import browser regression **1 passed**; JavaScript suite
**156 passed**. Ruff, strict maintainability, generated catalog verification and
`git diff --check` passed. Optional dependency tests were exercised locally with
motion-preview, ONNX runtime/model fixture, DICOM codecs and Chromium installed;
this does not substitute for reviewed real anatomical benchmarks.
