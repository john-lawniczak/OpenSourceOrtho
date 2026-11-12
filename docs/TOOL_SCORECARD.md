# Research tool scorecard after the improvement phases

These are engineering assessments, not measured dental accuracy or clinical
validation. Two decimal places follow the requested format; they do not imply
measurement precision. A 6.00 means a usable, inspectable research workflow with
source provenance, explicit limitations, and relevant regression checks. A 7.00
also requires stronger correction/recovery paths and broader known-input tests.
The previous scores are from the November 11 review.

| Tool area | Before | Now | Improvement and remaining limitation |
|---|---:|---:|---|
| Automatic surface segmentation | 4.75 | 6.00 | Optional connected surface-graph refinement and topology-based island repair; comparison runner against common reviewed labels. Anatomical boundaries and FDI identity remain unvalidated drafts. |
| Learned segmentation adapter | 4.00 | 6.00 | Hash-bound model contract, explicit features/tensors/FDI mapping, actual ONNX runtime test and output rejection. **This score covers integration only:** no trained dental weights were installed or anatomically benchmarked. Learned prediction quality remains unscored. |
| Boundary/label correction | 6.75 | 7.25 | Direct endpoint editor round trips, source checks, brush/split/merge/undo, return edits and invalidate/refit. Manual review burden is not yet measured on a reviewed real corpus. |
| Registration | 6.50 | 7.00 | Per-region reverse-cycle and resampling diagnostics, source-bound landmark fits with held-out errors, explicit patient/STL frames. Whole-arch fitting can still remove global motion; stable reference selection remains a review input. |
| Endpoint correspondence | 5.75 | 6.50 | Complete one-to-one match override with explicit holds and independent target regions; fit consistency and mismatches exposed. No independently adjudicated real identity-error rate. |
| Weekly simulation | 6.50 | 6.75 | Alternative timing, selected fitted-pair surface checks, refreshed diagnostics and explanations of held regions. Weeks 2–6 are estimates; timing, biology and actual path are not known. |
| Contact/proximity | 4.75 | 6.25 | Full-triangle distance/intersection checks catch triangle-interior crossings; budgets yield indeterminate. Closed-mesh containment, continuous swept contact and real bite accuracy remain gaps. |
| Two-visit workflow and persistence | 6.50 | 7.25 | Upload/correct/refit/save with portable hash-verified backups and non-overwriting restore. Browser storage is still local; collaborative case management is absent. |
| Accuracy benchmark tooling | 6.75 | 7.25 | Boundary IoU/precision/recall/context errors, identity checks, missing-fit coverage, strict real-review flags and 36 repeat/noise/resampling/partial-surface stress cases. **Patient accuracy remains unknown.** |
| CBCT/root/bone research workflow | 3.75 | 6.00 | Actual DICOM pixel decoding, three-plane viewing, bounded seed masks, affine/provenance-preserving proposals and explicit registration import. Intensity growth is not automatic tooth/root/bone identification; masks, landmarks and axis direction require review. Root proximity is explicitly a translation-only centerline approximation. |
| Opposing-arch/bite review | 5.50 | 6.25 | Shared-frame 3D inspection and rigid transform import bound to both scans and reviewer. No validated bite reconstruction or force analysis. |
| Local assistant / fit explanation | 6.75 | 7.00 | Bounded factual fit summaries, evidence references and review ordering, with finding lint before display. This improves local help; it does not establish external-model reasoning quality. |
| Shell/export QA | 6.50 | 6.75 | Full inner/outer surface separation supplements vertex sampling and downgrades incomplete or sub-feature checks. Manufacturing fit, containment and physical use are not established. |

All listed **research workflow** assessments now meet the requested 6.00 floor.
That statement must not be extended to trained-model accuracy, tooth identity
accuracy, root/bone segmentation accuracy or actual weekly motion: those remain
unverified. Features and synthetic tests cannot establish those scores.

## Evidence and reproducibility

See [the implementation phases](TOOL_IMPROVEMENT_PHASES.md),
[local CBCT instructions](LOCAL_CBCT_REVIEW.md), and the
[complete synthetic motion report](benchmarks/motion-stress-2026-11-11.json).
Reproduce that report with:

```sh
python tools/run_motion_stress.py --output /tmp/motion-stress.json
```

Six independently resampled no-motion pairs produced two false-motion cases at
0.05 synthetic-mm / 1-degree thresholds (mean rotation error 0.915 degrees,
maximum 1.759 degrees). This demonstrates why a visually smooth timeline is
insufficient evidence of accurate tooth motion. It is a single-region benchmark
with known identity; it does not test the full automatic segmentation pipeline.

The next accuracy milestone is a compatible, licensed trained model and an
independently reviewed real benchmark: both visits' tooth boundaries and identity
matches, reference-region justification, measured poses, and repeat acquisitions
with no intended movement. The existing STLs and CBCT make that review possible;
they do not themselves supply reviewed labels or motion truth.
