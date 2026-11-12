# Correcting tooth regions

Open **Edit tooth boundaries** under an uploaded scan to bring that surface into
the editor. Alternatively use **Correct tooth regions** in scan history, or
`/region-review.html`.
Load the sample baseline or your own STL, then optionally import its correction
JSON. Choose **Move view** to navigate; **Paint tooth** paints the chosen tooth number;
Split only paints faces belonging to the From tooth; Merge changes the complete
From region to the To tooth; Erase returns faces to context. Brush selection uses
surface position and normal agreement to avoid painting the opposite surface.
Undo/redo keeps up to 50 edit operations; each continuous brush drag is one operation. Save corrections exports face-order
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

1. Set **Scan arch** to **Lower**, then **Load USER_ONE baseline** to work from
   existing colored draft labels. For a private week 18 capture, set **Lower**
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
   current angle and fits the whole scan.
   Establish orientation and tooth numbering before painting. The numbered buttons
   use FDI, offer tooth names, and follow the loaded arch. Uncertain identities
   need notes, not guesses made to complete the labels.
3. Click a numbered tooth button, choose **Paint tooth**, and drag over its visible
   crown surface. The selected label is amber and the brush ring shows the radius.
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
5. Click **Save corrections** frequently. For a partial session, leave **I checked
   all tooth boundaries and numbers on this scan** unchecked. Record the inspected tooth IDs,
   surfaces, uncertainty, annotator role, and time alongside the JSON. The current
   checkbox describes the whole scan, not only the last painted tooth. Export
   preserves labels and source binding, not the undo stack or a detailed audit log.
6. Reload the same STL and correction JSON to check the round trip. Renaming an
   identical STL preserves its hash; a different capture needs separate labels.
   To collaborate here, provide the saved correction file's local path and the
   tooth/view you want reviewed. The assistant can inspect the saved artifact;
   it does not receive a live stream of pointer movements or unsaved brush edits.

Contributor markings remain contributor annotations. Independent review and
measured disagreement are still needed before using them as benchmark reference
labels. Defects in a scanned model must not be painted into imagined undamaged
tooth anatomy. Additional annotation controls are tracked in `TODO.md`.
