# Local CBCT pixel and mask review

Install `pip install -e ".[dev,motion-preview,volume-review]"`. The volume extra
includes pydicom and the lossless JPEG decoder used by USER_ONE's local files.
Prepare a local packet, keeping output in ignored storage:

```sh
python tools/prepare_cbct_review.py /path/to/IMGDATA --stride 4 --output datasets/CASE/.local/cbct-review-volume.json
```

Open `/volume-review.html` and choose the packet. Axial, coronal, and sagittal
views preserve the packet's voxel coordinates. Window controls affect display;
growth thresholds affect an explicitly seeded, bounded six-connected region.
Label a region with an FDI tooth number or `bone`, inspect its overlay in all
planes, undo/refine, then export draft masks. The cap is explicit and truncated
regions cannot be exported. ROI-edge contact is recorded. Intensity connectivity
is not tissue identity: connected tooth/bone structures or artifacts can merge.
Downsampling loses small details; use smaller stride for an appropriately cropped
source series when needed. No region is automatically assigned anatomical review.

The adapter orders slices by patient position projected onto the slice normal,
checks spacing/dimensions/orientation, applies per-slice rescaling, and preserves
the LPS voxel-to-patient affine. Missing/duplicate/irregular slices and sheared
stacks are rejected instead of silently reordered or stretched. Geometry follows
the [DICOM image plane specification](https://dicom.nema.org/medical/dicom/2026c/output/chtml/part03/sect_C.7.6.2.html).
Only the largest unambiguous single-frame series is selected. Enhanced multiframe
volumes are not supported by this adapter. No identifiers or filenames enter the
packet, but its pixels and derived anatomy remain private medical data.

Import the exported JSON through the existing **CBCT mask** control. Proposals
still require a human-accepted, quality-gated STL registration and explicit
anatomy review. Voxel indices are converted through the full affine; a rotated
volume no longer loses its origin/direction. Draft root centerlines use principal
axis bins in patient space instead of assuming roots follow the scanner Z axis.
The source digest identifies the preparation input for reviewer comparison; it
does not by itself prove that the selected case record is the correct study.

For a paired-landmark registration proposal, create `ortho-landmark-pairs-v1`
JSON with `units: "mm"`, `source_points_mm` (original STL coordinates),
`target_points_lps_mm`, `source_scan_sha256`, `volume_source_digest`,
`registration_id`, `source_stl_asset_id`, and `target_cbct_record_id`. Use at least
four spatially distributed, independently identified paired landmarks:

```sh
python tools/fit_cbct_landmarks.py pairs.json --source-scan scan.stl --volume-packet local-volume.json --output registration-review.json
```

The command verifies the source bindings and exports a proper rigid transform,
training residuals and leave-one-out residuals. Quality uses held-out RMSE.
`accepted` remains false. Review landmarks, coordinate frames, spatial coverage,
and held-out errors before importing/accepting the registration; a low residual
alone does not establish anatomy correspondence.

USER_ONE's 824-slice primary volume was decoded locally at stride 4 into a
225×225×206 review packet; the single secondary image was excluded. Browser tests
verify it renders without external requests. No real root labels or accepted
registration were fabricated during preparation.

Use **Import landmark registration report** in the root/bone workflow to load
`registration-review.json`, inspect the saved landmark/transform report, and
explicitly check **Registration accepted**. The import preserves its matrix and
measured quality; it does not replace them with manually entered defaults. The
server checks the selected scan/record IDs, scan SHA-256, millimeter units, and
mask volume digest. Patient-space masks require an explicit transform; the legacy
identity fallback is unavailable for these packets. Anatomy still starts as a
proposal after registration acceptance.

Downstream root-aware pivots convert the anatomy through its own registration
back to scan space. Root proximity translates scan-space vectors into the CBCT
frame before comparison. This proximity approximation explicitly excludes root
surface thickness and rotations. Different study frames or an unrelated accepted
registration cannot unlock these calculations.
