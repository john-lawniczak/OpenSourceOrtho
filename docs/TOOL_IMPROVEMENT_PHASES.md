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
