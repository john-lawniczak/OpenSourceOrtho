# USER_ONE week 18 lower cleanup draft

The contributor exported this exact browser save on 2026-11-13 and asked to
retain a useful cleanup version. `repair-bundle.json` preserves the edited STL,
painted labels, notes and four trim operations. Import it through **Edit Tooth
Precision → Import scan or corrections → Repair bundle**, then **Save edited
copy** to retain a browser copy. The original Fusion H4 observation remains unchanged.

This is useful for reducing excess model-base geometry, with a specific caveat:
66,640 faces were removed, including 66,612 unlabeled faces and 28 faces carrying
the automatic draft label 43 (about 0.34% of that label's prior surface area).
All 14 present tooth labels remain; retained face records and labels are exact.
The 43 margin needs inspection. Gray/unlabeled material is not automatically
non-tooth, so this remains an **unreviewed cleanup draft**. No hole fills were
applied. On November 15, 2026 the contributor explicitly selected this exact copy
for the local week-18 history display, alongside the cleaned upper. The local
endpoint verifies its hash and original H4 source and returns only geometry and
minimal provenance. This does not publish the bundle, transfer review, or turn
the approximate bite display into measured registration. The ordinary painting
link still opens original H4 with its source-bound labels.

`audit.json` quantifies removals against the original scan and its initial draft
painting. `removal-comparison.png` shows retained/removed geometry in three source
coordinate projections. Reproduce the audit from the repository root with:

```sh
.venv/bin/python tools/audit_surface_trim.py \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/private/surface-edits/week-18-lower-cleaned/repair-bundle.json \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/captures/fusion-h-4/2026-11-12_USER_ONE_lower_week-18_fusion-h-4.stl \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/private/painting-seeds/week-18/lower-corrections.json \
  --output /tmp/week-18-lower-cleanup-audit.json
```

These files incorporate local annotations into the private development dataset
only. They are excluded from public snapshots and static asset serving.
