# USER_ONE

Published longitudinal research case used by the browser and mobile samples.

- **Pseudonym:** `USER_ONE` (a display label, not a real-identity lookup)
- **UUID:** `07b70319-38c8-4b1a-9c98-517b8bc4cdd3`
- **Stable specimen ID:** `spec-07b7031938c84b1a9c98517b8bc4cdd3`
- **Visits:** baseline and first progress scan, confirmed as week 7
- **Publication scope:** [consent.json](consent.json)
- **Browse all cases:** [dataset catalog](../README.md)

The UUID is the existing case identity, preserved across all records. The
pseudonym does not replace it or identify a different participant. Original
scan bytes are unchanged. Metadata references are relative to this case root,
even when the referring JSON lives in `media/`, `derived/`, or `fixtures/`.


The case now includes a **first progress scan pair, reported as week 7**, under
the same specimen ID. See [the baseline/progress comparison and full case
timeline](outcome-notes.md), [machine-readable events](longitudinal-record.json),
and [redacted progress source metadata](progress-01-source-metadata.json).
The contributor confirms week 7 and reports five-day tray changes. The source
scanning date is September 17, 2026, 30 days after the recorded treatment start;
the progress label does not mean seven elapsed calendar weeks. The two new STLs
and six source-rendered JPEG views retain their original bytes with neutral
filenames. The contributor confirms validated cross-visit alignment and tooth
correspondence for the week 1/baseline and week 7 pairs (November 10, 2026).
Progress scale remains unverified. The viewer has not yet imported an executable
registration transform or per-tooth map.

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
simulation alone does not independently verify physical placement. The historical
tray-5 observation date and attachment placement date are not yet recorded.
For the progress update, the contributor reports five-day tray changes; the date
that schedule began is unknown.
`derived/attachment-transcription.json` records a partial model visual transcription of
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
- `progress-01-upper.stl` / `progress-01-lower.stl`: first progress scan pair
- `media/progress-01-*.jpg`: gallery and five individual source-rendered scan views
- `progress-01-source-metadata.json`: redacted progress provenance and hashes
- `longitudinal-record.json`: dated events, reported timing, and unresolved gaps
- `outcome-notes.md`: readable history, comparison, and reuse instructions
- `derived/progress-01-comparison.json` / `derived/progress-01-comparison.png`: reproducible
  geometry inventory and independent baseline/progress views
- `derived/attachment-transcription.json`: partial tooth-number transcription with
  frame evidence, a linted model finding, and unresolved posterior regions
- `treatment-context.json`: user-reported treatment dates, plan count, progress,
  IPR history, and attachment context; exact dates retained at the user's request
- `initial-upper.stl`: maxillary occlusion shell
- `initial-lower.stl`: mandibular occlusion shell
- `media/reference-media.json`: provenance metadata for a reference video whose
  bytes are excluded from this public snapshot
- `source-export-metadata.json`: redacted source-export metadata showing that
  the sample STLs correspond to the iTero `shell_occlusion` upper/lower jaw
  surfaces, with no separate bite STL present in the local export
- `cbct-metadata.redacted.json`: redacted structural CBCT companion metadata for
  the same sample case; raw DICOM bytes are intentionally not tracked
- `fixtures/root-bone-fixture.json`: safe derived anterior root/axis landmarks, fixture
  STL-to-CBCT registrations, and an alveolar-bounds record used to exercise the
  root/bone-aware sample workflow without committing raw DICOM bytes

These STLs are whole-arch scan shells, not segmented per-tooth meshes. They are
the exact models used by the in-app **Sample Test Case** (and named to match it).
The UI uses them to verify exact scan rendering and camera/material behavior. The
Sample Test Case pairs these scans with a simulated educational stage sequence;
it does not represent a clinical prediction, diagnosis, or treatment plan.

Local CBCT/DICOM for this same sample case may be attached on development
machines via the ignored `.local/local-cbct-record.json` sidecar and `.local/records/`
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

The reference video is omitted from this public snapshot because redistribution
rights remain unverified. Its descriptive metadata and explicitly unreviewed
attachment transcription retain their provenance references, not downloadable
video bytes. Earlier public Git history is unchanged. The reference is not an
outcome record, treatment approval, or evidence that the educational stage
sequence is clinically correct.

## Reported week 18

[Week 18 scans and model-damage notes](visits/progress-02/README.md) include the
original upper/lower pair and both Fusion H4/H6 lower captures. Public publication
was authorized on November 12, 2026; the existing week 1–7 motion fit is unchanged.

## Dentition and baseline annotation

The current [lower checkpoint](annotations/initial-lower-fragment-cleanup-2026-11-12T195642Z.json)
records the approved clearing of all 38 disconnected lower face labels to context
on November 12, 2026 at 14:56 EST (11 right, 27 left). All 14 lower labels now have
one connected region. The [cleanup audit](annotations/initial-lower-fragment-cleanup-2026-11-12T195642Z-report.json)
retains exact cleared indices and the previous painting's hash. Source triangles,
main connected crown regions and upper labels are unchanged. Both arches now
pass the one-connected-region-per-label check; anatomical boundary accuracy and
independent benchmark acceptance remain unverified.

The previous [lower painting checkpoint](annotations/initial-lower-painted-2026-11-12T194914Z.json)
preserves the contributor's specified local save from November 12, 2026 at
14:49 EST, including all 14 lower tooth labels (47–41 and 31–37). Its
[audit report](annotations/initial-lower-painted-2026-11-12T194914Z-report.json)
records source and version hashes, changes from the previous draft, and per-tooth
connectivity. The remaining 11 right-side and 27 left-side disconnected faces
are retained for inspection. Painting is still a draft pending independent
boundary review; source geometry is unchanged. The earlier lower valley recipe
and width report describe the preceding draft, not this saved painting.

The contributor reports that the wisdom teeth (FDI 18, 28, 38, 48) were removed.
Extraction dates and any other absent teeth are unspecified. Upper second molars
are 17 / US 2 and 27 / US 15. See `treatment-context.json`.

The current [upper checkpoint](annotations/initial-upper-fragment-cleanup-2026-11-12T190542Z.json)
records the contributor-approved clearing of all remaining disconnected upper
label patches on November 12, 2026 at 14:05 EST. The remaining 144 left-side face
labels were cleared to context; with the prior 116 right-side faces, this totals
260 cleared label memberships. All 14 upper labels now have exactly one connected
region. The [cleanup audit](annotations/initial-upper-fragment-cleanup-2026-11-12T190542Z-report.json)
retains exact face indices and the previous checkpoint hash. Original geometry,
main connected crown regions and lower labels are unchanged. Connectivity is
verified; independent anatomical boundary review and benchmark acceptance remain
pending.

The previous [right-side cleanup checkpoint](annotations/initial-upper-right-fragment-cleanup-2026-11-12T190354Z.json)
records the contributor-approved clearing of 116 detached upper-right face labels
to context on November 12, 2026 at 14:03 EST. All seven upper-right labels now
have one connected region. Upper-left memberships are unchanged, including their
144 detached faces pending inspection. The [cleanup audit](annotations/initial-upper-right-fragment-cleanup-2026-11-12T190354Z-report.json)
retains the exact cleared face indices and links the preceding labels by hash.
Scan triangles were not deleted or changed; anatomical benchmark review remains
incomplete.

The previous [upper painting checkpoint](annotations/initial-upper-painted-2026-11-12T184456Z.json)
preserves the contributor's explicitly identified save from November 12, 2026
at 13:44 EST. The contributor confirms both upper sides (FDI 11–17 and 21–27)
are painted correctly. The [checkpoint audit](annotations/initial-upper-painted-2026-11-12T184456Z-report.json)
records all 14 labels and the remaining connectivity issues: 116 right-side
and 144 left-side faces lie outside their label's main connected component.
These faces are retained for inspection. Anatomical accuracy is not independently
verified, the saved reviewed checkbox remains false, and the one-region-per-tooth
benchmark criterion is not yet met. No lower-arch confirmation is inferred.

The previous [upper-left painting checkpoint](annotations/initial-upper-left-painted-2026-11-12T182629Z.json)
records the contributor's painting saved November 12, 2026 at 13:26 EST.
The contributor confirms the patient-left upper teeth (FDI 21–27) are painted
correctly. This confirmation is recorded without independent anatomical
verification; at that checkpoint, right-side painting was still pending.
The [painting report](annotations/initial-upper-left-painted-2026-11-12T182629Z-report.json)
records all 7,237 changed faces, including edits at the 11/21 boundary, and links
the prior checkpoint by hash. Saved labels are preserved exactly.

The earlier [context-cleanup checkpoint](annotations/initial-upper-context-cleanup-2026-11-12T181002Z.json)
records the contributor's context cleanup saved November 12, 2026 at 13:10 EST.
It clears 42,307 previously labeled faces to context, without reassigning any
tooth numbers. All 14 upper labels remain. The [checkpoint report](annotations/initial-upper-context-cleanup-2026-11-12T181002Z-report.json)
records per-tooth counts and hashes linking the previous and current versions.
This is a draft before final painting, not a reviewed segmentation benchmark.
Original scan geometry and the local editing history are unchanged.

The previous [geometry-assisted upper draft](annotations/initial-upper-tooth-corrections.json)
retains painted front surfaces, aligns side numbering with the contributor's
confirmed 21/22 anchors, and splits posterior masks into premolar/first-molar/
second-molar labels. The [recipe](annotations/initial-upper-posterior-recipe.json)
and [report](annotations/initial-upper-posterior-report.json) describe the
geometry-assisted separators and remaining uncertainty. The previous annotation
is retained alongside them. The draft is not fully reviewed crown segmentation;
it does not replace the week 1–7 motion artifact. Reproduce that historical
geometry-assisted draft with the command below; it does not reproduce the later
manual cleanup:

```bash
python3 tools/correct_user_one_upper_labels.py datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3
```

The contributor also confirmed the previously gray upper-right front crowns as
11 / US 8 (central) and 12 / US 7 (lateral). Their original draft masks are
restored only where faces were unlabeled; existing colored surfaces are unchanged.
The before-restoration annotation is retained for comparison. These crown masks
still need boundary review.
