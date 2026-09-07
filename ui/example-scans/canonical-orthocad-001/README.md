Canonical OrthoCAD scan fixture used by the browser UI.

The user confirmed that the upper/lower STL pair was acquired on **June 5, 2026**,
**before treatment**, and that the companion CBCT is from the **same person**.
The manifest labels both STLs as `initial`; `source-export-metadata.json` records
the user-confirmed acquisition date and pretreatment status. This acquisition
date is distinct from the manifest creation timestamp. The exact STL and CBCT dates are
retained at the user's explicit request; it is an exception to the usual
date-redaction guidance for contributed records.

The user confirmed that the CBCT was acquired on **June 18, 2026**, **13 days
after the STL pair**. `cbct-metadata.redacted.json` records this user-confirmed
date; it has not been independently verified against DICOM tags. Treatment began
on **August 18, 2026**, so both scan acquisitions precede treatment. The user
confirmed that **no IPR had occurred as of June 18**; later IPR status is unknown.
Same-person provenance does not
establish same-session acquisition or a validated STL-to-CBCT registration.

The user reports a **38-tray plan**, **tray 5 at the time of the report**, and
attachments present. **The user confirms that actual attachment locations match
the reference video.** This is user-confirmed placement correspondence; the
simulation alone does not independently verify physical placement. The progress
observation date, wear interval, and attachment placement date are not yet recorded.
`attachment-transcription.json` records a partial model visual transcription of
the red attachment markers using FDI numbering: **11, 12, 33, 34, 43, 44**.
It includes tooth names, Universal numbering equivalents, video timestamps, and
pixel locations. This assumes a standard non-mirrored frontal view. Additional
upper posterior markers cannot be assigned reliably from this view and are
recorded as unresolved regions; the six teeth are not a complete inventory.
The model finding passed `lint_finding()` before export; this checks finding
language, not anatomical correctness. Independent tooth-number review remains
outstanding. Your confirmation that placement matches the video is retained
separately from the model's numeric transcription. Tray 5 is a
historical user report, not live status. `treatment-context.json` preserves these
facts and unknowns; the manifest includes the confirmed plan stage count.

Files:
- `attachment-transcription.json`: partial tooth-number transcription with
  frame evidence, a linted model finding, and unresolved posterior regions
- `treatment-context.json`: user-reported treatment dates, plan count, progress,
  IPR history, and attachment context; exact dates retained at the user's request
- `sample-test-case-upper.stl`: maxillary occlusion shell
- `sample-test-case-lower.stl`: mandibular occlusion shell
- `sample-test-case-cliniccheck-reference.mp4`: cropped/debranded reference
  simulation associated with the same source STL pair
- `reference-media.json`: non-clinical metadata for the reference video
- `source-export-metadata.json`: redacted source-export metadata showing that
  the sample STLs correspond to the iTero `shell_occlusion` upper/lower jaw
  surfaces, with no separate bite STL present in the local export
- `cbct-metadata.redacted.json`: redacted structural CBCT companion metadata for
  the same sample case; raw DICOM bytes are intentionally not tracked
- `root-bone-fixture.json`: safe derived anterior root/axis landmarks, fixture
  STL-to-CBCT registrations, and an alveolar-bounds record used to exercise the
  root/bone-aware sample workflow without committing raw DICOM bytes

These STLs are whole-arch scan shells, not segmented per-tooth meshes. They are
the exact models used by the in-app **Sample Test Case** (and named to match it).
The UI uses them to verify exact scan rendering and camera/material behavior. The
Sample Test Case pairs these scans with a simulated educational stage sequence;
it does not represent a clinical prediction, diagnosis, or treatment plan.

Local CBCT/DICOM for this same sample case may be attached on development
machines via the ignored `local-cbct-record.json` sidecar and `records/`
symlink. The tracked `cbct-metadata.redacted.json` file records the current
gold-standard structural facts: the primary volume is a contiguous 824-slice CT
stack at 900x900 with 0.2 mm in-plane spacing and 0.2 mm slice thickness, plus
one secondary CT object that is not part of the primary stack. Keep the raw DICOM
series outside git unless it has been explicitly de-identified and redistribution
rights are confirmed; this repository's plan fixtures should carry only redacted
metadata or reviewed derived anatomy.

The root/bone fixture is a deterministic engineering fixture. It is accepted by
the app so the Sample Test Case can demonstrate the full registration,
anatomical-frame, root/bone-review, and CBCT-boundary-prior pipeline. It is not a
clinical segmentation, diagnosis, clearance, or treatment approval.

The reference video is retained only as comparison material for the sample case.
It is not an outcome record, not a treatment approval, and not evidence that the
sample educational stage sequence is clinically correct. Confirm redistribution
rights before sharing the media outside a private/local dataset.
