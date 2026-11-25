# Capture provenance and repeatable acquisition

Added November 25, 2026. This workflow supports a clear-aligner planning safety
playground and research toolkit. Its reports describe provenance and comparison
limits; they do not establish anatomical accuracy or physical-use readiness.

## Why this change

Commercial processes provide useful engineering examples. [Sentinel describes](https://sentinelmouthguards.com/blogs/mouthcare/how-custom-night-guards-are-made)
inspecting and digitizing an impression, printing a dental model, pressure-forming
and inspecting the appliance. [MOSES requires a digital intraoral scan](https://moses.com/products/unplastic-retainer)
and describes shaping PHA over a model derived from it. [Align's 2025 annual report](https://www.sec.gov/Archives/edgar/data/1097149/000109714926000014/algn-20251231.htm)
describes printing stage-specific molds after clinician approval, then pressure-forming
sheets. These are manufacturer accounts, not independent accuracy measurements.
They motivate preserving each acquisition stage and checking defects before using
a derived surface as evidence. They do not establish a recipe for autonomous treatment.

USER_ONE week 21 exposed concrete failure modes: C1/C2/C3 are separate captures
of one cast, with highly correlated C1/C2 surfaces; C4 is chipped; C6 was fractured
into two pieces and held together with clay. A connected mesh can still represent
a physically broken specimen. File count is not independent sample count.

## Implemented behavior

Each `ContributedScan` can now carry optional typed `acquisition` metadata:

- capture kind: intraoral, cast, negative impression, aligner, printed model, or unknown;
- acquisition date, pseudonymous physical-object ID and capture-session ID;
- measured surface, physical condition, fragment count and support material;
- scanner/material, coating status/product, processing operations and digital-parent hashes.

Keep IDs pseudonymous and free text free of identifying information. Digital-parent
hashes declare provenance links; this review does not load or verify those parent
artifacts. The scan's existing SHA-256 binds the review to its actual file.
`processing: []` means explicitly reported no processing; the default is unknown.
An unchanged original export can still include the scanner software's fusion or
smoothing, so byte preservation does not establish unprocessed geometry.

`orthoplan review-captures MANIFEST --out REVIEW.json` verifies every scan hash,
rejects symlinked scan files, protects source scans/manifest from output overwrite,
and emits deterministic, linted findings. It groups repeats by physical-object ID
and reports distinct file hashes and recorded sessions without declaring independence.
Legacy manifests remain valid and report unknown acquisition provenance.

Damaged, impression, appliance, printed-model and unknown captures are excluded
**as intact-arch references in this provenance report**. They remain available for
exploratory inspection and comparison. Cast and intraoral records never receive an
automatic accuracy endorsement: their reference status stays not established.
These labels do not change existing observed weeks, segmentations, motion fits,
unit settings or clinical review state. When acquisition metadata is supplied,
longitudinal bounds-error reports also withhold numeric tooth-tracking proxies
for non-intraoral or damaged captures. Legacy records retain their existing unit
and geometry checks. Recursive benchmark discovery now skips hidden/local and
private folders; an import-review manifest must not become a public case observation.
This is not a universal enforcement gate on every upload/export path.

The week 21 companion panel shows the generated provenance review next to original
STL downloads. Nested findings pass `lint_finding()` before display or summary
export. The existing individual consent and hash checks continue to apply.
Reports and comparisons retain acquisition interpretation separately from distances.
No hosted inference, new registration fit or geometry modification is performed.

The week 21 upper negative impression is now attached as a separate companion
panel with original STL, six views, projected open edges, a subjective assessment,
and its own manifest under `visits/progress-03/impressions/`. Its November 24 capture
date is separate from November 23 impression-taking and November 25 import/export.
Downloads use the existing consent/hash checks, and interpretations pass the finding
lint before display. An absent impression bundle does not hide the dental visit or
cast records; an impression never replaces the observed upper dental surface.
The lower impression is preserved in `impressions/lower/` with its own manifest,
assessment and hash index. The companion API's `impressions` field is now a list
of independently consented records, each with a server-selected asset prefix.
The viewer shows both records with distinct download and inspection links; missing
or revoked upper assets do not prevent a consented lower record from appearing.
Both impression dates and capture dates are contributor-confirmed. They remain
separate from the original dental bite coordinates and inferred motion.
Physical-impression photographs are separately consented, hash-checked companion
assets. Their records distinguish same-condition confirmation from photo capture
date; the latter remains unknown here. The viewer omits revoked or hash-mismatched
photo links without hiding the underlying impression scans. EXIF orientation was
applied and decoded RGB pixels saved losslessly without embedded metadata; original
JPEGs remain local. The photos add physical context without changing scan scores
or asserting a mapped cause for each mesh opening.

## Example: an impression capture

Add this to the appropriate scan entry in a contribution manifest, retaining its
actual filename, hash and geometry counts. This is a template, not a newly acquired
USER_ONE record. Use the impression's actual capture date, not the file-save date.

```json
"acquisition": {
  "kind": "impression_scan",
  "physical_object_id": "week-21-lower-impression-1",
  "capture_session_id": "impression-session-1",
  "surface": "negative_impression",
  "condition": "unknown",
  "coating": "none",
  "processing": ["unknown"]
}
```

From the repository root:

```sh
python -m orthoplan.cli review-captures \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/personal-models/manifest.json \
  --out /tmp/week-21-capture-review.json
```

For edits to the bundled cast manifest, rebuild its assessment and download index
using `PYTHONPATH=. python <bundle>/build_assessment.py`, then regenerate the catalog
with `python tools/build_dataset_catalog.py`. Changes to a comparison's acquisition
metadata also require regenerating that report. Keep original STL bytes untouched.

## Next acquisition experiment

1. Preserve the existing week 21 dental pair and its exported bite coordinates.
2. If C5 remains unchanged, compare a lab scan with the home scan of that same
   physical cast. This better separates scanner differences from casting differences;
   neither instrument becomes exact ground truth by designation.
3. If an original week 21 impression remains intact, collect a negative-impression
   scan and compare a documented lab reconstruction with the dental reference.
   This tests acquisition without pouring another cast. Changing normals alone
   does not recover missing cavity surfaces or validate reconstruction.
4. Record each independent capture separately before merging. Compare coverage,
   repeatability and regional residuals, retaining missing areas and damaged
   specimens. Do not rescale/deform meshes to force agreement or substitute filled
   surfaces for measured tooth anatomy.

An impression taken later is a later observation, even if the person is still
wearing the tray labeled week/stage 21. Keep impression date, scan date and stage
label distinct. A scan of an old impression records its present physical state;
record storage and any changes rather than assuming unchanged dimensions.

## Clear aligners and coatings

Do not paint, dye, mark, powder or apply industrial scanning spray to a current
aligner or a backup that might return to the mouth. Do not use the bench scanner
inside the mouth. [3DMakerpro's Fox page](https://store.3dmakerpro.com/products/fox)
notes difficulty with transparent/reflective surfaces and suggests matting spray
for objects. That is not evidence of compatibility with a wearable appliance.
[AESUB's FAQ](https://aesub.com/insights/faq/) describes the optical purpose of a
matting layer and its effect on the measured surface; evaporation claims do not
establish oral-contact compatibility or preservation of aligner properties.

For a retired appliance that the clinician confirms is no longer needed as a
backup, begin with an uncoated bench feasibility scan. Support it without bending
or obscuring the surface being recorded. Capture inner and outer surfaces as
separate records and preserve raw projects/exports. Reposition the object to inspect
coverage; do not assume software-filled pockets are measurements. Transparent
material may simply fail to yield a useful scan with this equipment.

If coating is necessary, restrict it to a permanently non-wearable research
specimen and follow the product's material-compatibility guidance and SDS. Record
the coating and treat thickness as an additional unknown. Household paint/marker
is not a measurement-preserving substitute. Do not infer the inner surface by
subtracting a uniform thickness from an outer scan. Do not pour casting material
into a current wearable tray.

Tray scans are appliance proxies: wear, forming, relief, attachments and thickness
separate them from actual tooth surfaces and proprietary target setups. A tray's
stage number is not a verified treatment-week date. Prioritize an intact impression
or same-cast repeat over a coated tray when studying acquisition accuracy.
