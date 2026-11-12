# Correcting tooth regions

Open **Paint tooth boundaries** in the app sidebar or in Guided **step 2: Teeth
& time**, after loading scans and before building movement stages. Scan history
also links directly to each USER_ONE baseline. **Edit tooth boundaries** under
an uploaded scan brings that surface into the editor. The direct URL is
`/region-review.html`. This is a scan-labeling task, not an aligner stage; for
USER_ONE it uses the week 1 baseline, with separate upper and lower annotations.
Load the sample baseline or your own STL, then optionally import its correction
JSON. Choose **Move view** to navigate; **Paint tooth** paints the chosen tooth number;
Split only paints faces belonging to the From tooth; Merge changes the complete
From region to the To tooth; Erase returns faces to context. Brush selection uses
surface position and normal agreement to avoid painting the opposite surface.
Undo/redo keeps up to 50 edit operations; each continuous brush drag is one operation. Download corrections JSON exports face-order
labels bound to the source SHA-256; applying to another scan is rejected.

Explicitly checking the review checkbox records the user's boundary review.
It does not approve fitted motion or anatomy. The fitting engine can consume
corrections for either endpoint and preserves their supplied crown masks rather
than cropping them again. Existing automatic segmentation remains a fallback.

To compare a stronger installed segmentation plug-in against the hybrid baseline,
use the existing `orthoplan segmentation-benchmark --manifest <reviewed-corpus>`
workflow described in `segmentation-learned-backend.md`. No new model weights or
reviewed corpus have been supplied in this change, so no superiority score is
claimed. The independent motion scorer in `MOTION_BENCHMARK.md` complements that
boundary benchmark with correspondence and pose errors.

## A first contributor review session

With `orthoplan serve` running, open
[Review tooth regions](http://127.0.0.1:8000/region-review.html).
Start with a few clearly visible teeth, rather than marking an entire arch as
reviewed at once.

1. Choose **Paint upper baseline** or **Paint lower baseline**. The editor
   restores the latest local save for that arch, or starts with colored draft
   labels if none exists. It never silently defaults to an upper scan. Changing
   the arch selector while editing a baseline loads the matching baseline and
   numbers; an unsaved-work prompt protects edits before replacing the scan. For a private week 18 capture, set **Lower**
   first and choose its local STL through **Own STL**, or use **Edit tooth boundaries**
   from the main uploaded-scan viewer. A filename containing an unambiguous lower/upper
   arch label sets the import arch. A newly loaded own scan
   starts gray/unlabeled; import matching correction JSON if available. Private
   files do not need to be added to the public catalog or asset allowlist.
2. Use **Auto view** to fit the scan, then **Face-on**, **Above**, **Side**,
   **Other side**, or **Roll left/right** to choose an angle. **Move view** enables
   drag-to-rotate, scroll/pinch-to-zoom, and right-drag-to-pan. Auto view uses the
   thin bounding-box axis as a starting estimate, not a verified anatomical frame.
   These controls change only the camera; original face order, coordinates,
   source hashes, and fitted poses stay unchanged. **Fit scan** preserves the
   current angle and fits the whole scan. Side **+ Zoom in / − Zoom out** buttons
   change camera distance without changing labels.
   Establish orientation and tooth numbering before painting. The numbered buttons
   use FDI, offer tooth names, and follow the loaded arch. Uncertain identities
   need notes, not guesses made to complete the labels.
3. Click a numbered tooth button. Its full name and position from the midline
   appear beside the scan; the loaded upper/lower arch and numbering range stay
   visible. Existing faces for that label turn amber with a numbered location
   marker, while other labels retain their colors by default. **Find selected label** centers
   and fits its region; rotate if it is behind visible surfaces. These are draft
   label locations, not confirmed tooth identities. In **Move view**, clicking
   a labeled surface selects its number without painting. **Show other label
   colors** is on by default; turn it off to mute other regions. **Show label
   flag** independently hides or shows the numbered marker.
   If no faces carry a number, the editor says there is nothing to highlight;
   use the location guide and confirm which crown it is before painting. A tooth
   number alone cannot locate an unpainted or missing tooth.
   Choose **Paint tooth** and drag over its visible crown surface. The brush ring
   shows the radius. Press **[** to decrease or **]** to increase it by 0.1 scan
   units, bounded to 0.1–10; matching buttons sit beside the radius field. These
   shortcuts do not intercept typing in text, numeric or dropdown fields.
   The instruction panel names the active tooth and reports its labeled face count.
   Use a smaller radius near tooth/gum transitions and neighboring teeth. This
   paints mesh faces; drawing only an outline does not fill the enclosed crown.
   Rotate and check both sides. The position/normal filter reduces accidental
   opposite-surface painting but does not guarantee correct anatomical boundaries.
4. Use **Erase to context** to remove gum or extra surface from a tooth label;
   **Split selected source** transfers only the From region under the brush.
   **Merge from → to** changes the entire source region. Split, numeric From/To,
   and merge controls are under **Advanced: split or merge labels**. Undo mistakes promptly.
   Mark uncertain boundaries and model defects in accompanying notes/view images;
   the current editor has no dedicated uncertainty or defect layer.
5. For USER_ONE baselines, use **Save locally** frequently. Partial work keeps
   **I checked all tooth boundaries and numbers on this scan** unchecked. Add
   uncertainties, missing tooth identities and chip observations in **Notes**.
   When the entire arch has been checked, check the review box and save again.
   Each save creates an immutable timestamped JSON snapshot under
   `.orthoplan-region-corrections/USER_ONE/baseline-upper/` or `baseline-lower/`.
   The UI displays the exact local path and separate saved status for each arch.
   These files survive browser/server restarts and remain outside Git by default.
   `ORTHOPLAN_REGION_CORRECTIONS` can select another local storage directory.
6. Load the same baseline to resume its latest snapshot, including notes and
   review status. **Download corrections JSON** gives a portable face-label
   record for any scan; use **Load saved correction JSON** with the identical
   scan to import it. Local snapshots also preserve source identity, notes,
   timestamp and review status; neither save format preserves undo history.
   Server saves validate source hash, face count and arch-specific FDI IDs before
   writing. A failed save is shown explicitly. Existing snapshots are retained.
7. When upper and lower are complete and saved, tell the collaborator **both
   baselines are saved**. They can inspect the local files, validate source
   binding and boundary quality, then incorporate approved annotation versions
   into the private dataset and regenerate comparisons deliberately. Saving
   alone does not replace bundled motion previews, refit endpoints, train a
   model or establish benchmark ground truth. The assistant can inspect saved
   artifacts but does not receive unsaved pointer movements or brush edits.

FDI numbering distinguishes arches: **11–18** upper right, **21–28** upper left,
**31–38** lower left, and **41–48** lower right. For example, 18 is an upper right
third-molar position. Only numbers for the loaded arch appear. These are possible
positions, not evidence that every tooth is present or correctly identified in
the draft labels. Do not paint a missing tooth merely because it has a button.

Contributor markings remain contributor annotations. Independent review and
measured disagreement are still needed before using them as benchmark reference
labels. Defects in a scanned model must not be painted into imagined undamaged
tooth anatomy. Additional annotation controls are tracked in `TODO.md`.
