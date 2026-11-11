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
