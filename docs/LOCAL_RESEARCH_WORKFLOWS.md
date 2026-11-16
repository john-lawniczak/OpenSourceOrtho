# Saved labels, captures and recoverable edits

These local tools extend the exploratory workflow. Original scans, inferred
history and applied planning edits remain separate.

## November 15, 2026 — local family profiles

Gear **Settings → Profiles** offers separate local workspaces, **Add profile**,
**Rename**, and **Save progress**. A dropdown beside **Your Teeth Profile** provides
quick switching without a separate profile bar. Existing data stays in **My profile**. Main
workspace progress saves automatically and before switching; paintings still
save explicitly in their editor. Browser and server records are separated by
profile, with stale-workspace protection. See [local profiles](LOCAL_PROFILES.md)
for saved data, migration, browser-local limits and verification.

## November 15, 2026 — week 18 observed display

Scan history now selects the cleaned upper and, when the private saved bundle is
present, the contributor's explicitly chosen trimmed H4 lower. Following the report
that the pair looked warped, crown-row inspection frames replace the initial
rounded rotations and whole-model outline anchors. Draft tooth centers level
the arches, incisor midlines center them, and a shared depth offset centers side
views. Individual-arch views center the whole model, and week-18-specific viewport
bounds prevent clipping without changing earlier weeks' framing. Original scale
and geometry are retained; cast-base bulk no longer sets
the alignment. The visible label says **approximate bite display**: this is neither measured
bite registration nor a week-18 motion fit. Earlier week views retain their
geometry and camera placement. Original scans and source-bound painting saves
are preserved.

The selected lower copy is checked against its exact hash and original H4 source.
The local endpoint returns geometry and minimal provenance, excluding annotations
and notes. Public installations without that private bundle use explicitly named
original H4. Invalid copies fail visibly. See [scan history](SCAN_HISTORY.md#observed-week-18)
for capture selection and the local endpoint. Restart the local Python server and
refresh the browser after updating to load this endpoint.

Validation: 20 focused JavaScript checks, 2 Python checks, and 5 affected browser
workflows passed; front/side screenshots were inspected. Earlier scan pixels,
loading failure/retry, and painting save/reopen were checked. Ruff, strict
maintainability, and diff whitespace checks passed. These verify software behavior,
not anatomical accuracy. H4/H6 repeatability measurement remains unimplemented.

The alignment follow-up additionally checks proper rigid transforms, unchanged
vertex coordinates and distances, crown-frame invariance to extra cast-base
geometry, source-hash rejection, and independence from earlier visit placement.
The view remains an unreviewed arrangement; it cannot establish actual occlusion
or correct surface defects already present in the physical-model scans.

## November 15, 2026 — stronger surface trimming

The H6 cleanup report exposed a screen-resolution selection limit: the old picker
could record only one triangle per pixel, leaving dense subpixel triangles behind.
The removal brush now supplements visible face IDs with depth-checked projected
triangle centers, includes a one-pixel depth band for near-surface roughness, and
covers the path between pointer events. This improves dense surface selection and
fast sweeps while excluding deeper occluded geometry. It is not an opacity
adjustment; selected faces are fully deleted.

At the contributor's request, **Apply trim** is now the only approval for deleting
the red selection, including painted faces. The redundant checkbox is removed,
and the selection count identifies painted faces before applying. Deselect/Clear,
Undo surface edit, separate-copy provenance, and save/reopen remain available.
This changes the editor, not any existing H6 save or original scan. Review and
save the intended cleanup explicitly. See [surface cleanup](REGION_CORRECTIONS.md#clean-up-model-surface).

Validation covers dense flat/tilted surfaces, nearby roughness, hidden back layers,
fast strokes versus separate clicks, painted-face approval, undo/save/reopen, and
a temporary trim/undo on the original H6 scan. The changes do not assess the
anatomical correctness of a contributor's removal selection.

## Prepare an H4/H6 repeatability check

H4 and H6 are captures of the same physical lower model. On November 15, 2026,
the contributor confirmed no physical changes between these scans and that the
chip was already present in both. This supports evaluating apparent tooth motion
as capture/fitting inconsistency; it is contributor evidence, not independent
verification. The contributor now tentatively identifies the chip near **FDI 32**,
reports protruding material in H6, and considers the other teeth relatively
accurate by visual inspection. The exact defect surface remains unmapped; neither
scan is established reference geometry. JMStudio exports are reported in
**millimetres**. This is recorded as export-unit provenance, separate from
exact-file settings and dimensional calibration; no geometry is rescaled.
Acquisition dates remain unknown. Later digital trimming is separate from
physical-model changes.

The contributor supplied the **edited H6 copy** with six trims and 442,757 faces.
H4-derived draft colors were transferred through original H6 onto exact retained
face records: 14 tooth regions, 135,761 painted faces. Every geometry byte and the
complete trim history are unchanged. This copy had no existing painted faces;
the transfer preserves existing nonzero labels when present. The draft remains
unreviewed, especially FDI 32, partially covered FDI 41, and protruding material.
No original-H6 painting was installed and no repeatability report was produced.

The private output lives in
`.orthoplan-region-corrections/USER_ONE/edited-h6-draft/`; the full repair bundle
is `H6-cleaned-painted-draft-repair.json`. For the existing browser save, reopen
the six-trim H6 copy from **My Notes**, expand **Import scan or corrections**, load
`H6-cleaned-painted-draft-corrections.json` into **Correction JSON**, inspect, then
**Save locally**. The corrections are bound to that exact cleaned mesh hash;
using a more recently trimmed copy requires another transfer. The full repair
bundle is a portable backup. Keep the original unpainted export too.

`tools/paint_edited_h6.mjs` validates the bundle using the editor's importer,
matches retained binary face records, rejects changed geometry, and writes a new
file without overwriting an existing one. Browser checks cover automatic-draft
provenance, geometry/trim/label round trips, and correction import into an existing
saved copy. These check preservation and workflow, not segmentation accuracy.

1. Open **Paint USER_ONE week 18 lower** to review original H4 and its saved labels.
   Start with an intact front tooth, premolar and molar. Check each tooth number
   and boundary from front, inside and biting-surface views.
2. Record the reviewed tooth numbers, uncertainty and chip location in **Notes**,
   then **Save locally**. Leave the whole-scan reviewed checkbox off for partial
   review. This is contributor review, not independent reference labeling.
3. Open `/region-review.html?baseline=lower&visit=progress-02&capture=fusion-h-6`
   on the same local server. H6 may start unpainted. Paint/check the same intact
   teeth and save its separate source-bound record; never copy H4 face labels
   onto H6. The ordinary week-18 lower button continues to select H4.
4. Associate the reported JMStudio millimetre setting with the exact files and
   retain its contributor provenance. Unconfirmed file scales remain in scan
   units. Retain the November 15 unchanged-model confirmation with the report.

The history viewer uses trimmed H4 locally, but the ordinary lower painting link
opens original H4. The repeatability experiment should explicitly select original
H4/H6 or separately record any tested trimming variant; never silently mix them.

The remaining coding task is a reproducible report: retain exact scans, labels
and settings, align the scans in several ways, and repeat with different sampled
surface points. Report how apparent movement changes, with coverage and unmatched
teeth. The contributor supplies reviews and provenance; painting alone does not
run this experiment. Results will measure capture consistency, not reconstruct
missing tooth surfaces or establish tooth-motion accuracy.

## Refit USER_ONE from saved painting

In **Scan history → Scan details & match quality → Saved-label experiments**,
choose upper or lower, then **Refit saved painting**. This uses the current week 1
and week 7 labels. When week 7 painting is unavailable, the fixed local hybrid
segmenter supplies a draft fallback; it does not block an exploratory preview.

Each result retains both original scan hashes, rotations, units, frozen label
snapshots and hashes, generator/configuration and pipeline-code fingerprints.
It records fitted/uncertain/unmatched counts, mean per-region p90 surface
residual with its denominator, the bundled-fit summary and previous-fit summary.
The bundled artifacts and earlier experiments are never overwritten. Choose
**Bundled fit** or a saved fit explicitly. Changed inputs mark earlier fits stale;
their reports remain available, but regenerating is required to display them as
current estimates. Original observations stay available.

The preview still labels intermediate weeks as estimates. Surface agreement,
including lower residuals or fewer weak matches, does not establish tooth-motion
accuracy. Whole-arch registration and unverified scale retain their limitations.

**Compare automatic labels** compares the bundled automatic *moving/target face
masks* with a frozen copy of current contributor painting on the same original
faces. These bundled masks include the existing crown cropping and endpoint
transfer, so they are not an independent segmentation reference. Reports include
FDI-specific IoU/precision/recall, per-reference label confusion counts, missing
identities, coverage counts and explicit denominators. Unpainted reference faces
are unknown, not established gum. Boundary distances, correction time, automatic
segmentation runtime and independent anatomical accuracy remain unavailable.

Fits, review events and reports live in ignored `.orthoplan-research/` directories
(or `ORTHOPLAN_RESEARCH_STORE`). Downloads contain contributor annotations and
remain private unless separately authorized. No hosted model is called.

## Durable contributor reviews

On **Explore individual teeth**, select a crown, check its number/boundary, and
optionally add your name, notes or uncertainty under **Review notes**. Saving is
required before the review enables a movement preview. “Uncertain” and “unchecked”
do not enable editing. This is a self-reported contributor review, not independent
clinical review.

A review binds the original source hash, FDI identity and exact region mask.
Changing that region or source invalidates it on reload; changing an unrelated
region does not. Review history is append-only. It does not promote fitted poses
or confer review on another tooth. Review persistence currently covers USER_ONE
painted scans; generalized uploaded-case reviews remain backlog work.

## Alternative captures at the same visit

**Compare two scans** accepts several STL files per endpoint. Use **Active
capture** to choose which one enters the fit. Alternatives stay within that
visit and arch; they do not create extra weeks. Each capture retains its original
bytes/hash, capture date, local import time, model/cast ID, damage notes,
orientation and corrected labels. The model ID is contributor-entered evidence,
not proof that two captures share a cast.

Save both selected visits before fitting if desired. Local saves and v2 portable
backups retain all alternatives and the active choices; v1 backups still open.
Switching captures invalidates the current fit and match overrides. Imports are
bounded to eight captures per endpoint, 100 MB per scan and 180 MB per case.
A general multi-visit graph, composite models and measured repeatability are
separate future work.

## Undo, redo and recovery

Applied tooth previews support **Undo** and **Redo**. Applying a new change after
undo clears the old redo branch. Pending proposals remain separate and cannot be
restored as applied edits.

Applied movements and hold choices save in the browser's IndexedDB. Reopen the
same scans and painting, then use **Recover applied edits → Restore edit session**.
The stored source/label binding and scan-unit settings must match. Restoring
replaces the working rows and hold choices and recovers up to 20 undo/redo steps;
it does not restore API keys, review flags or unpublished proposals. Browser
storage is local to the server address/profile. Existing plan-version exports
remain the portable path; named alternative editing branches are not added here.
