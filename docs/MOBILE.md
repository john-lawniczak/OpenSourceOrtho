# Mobile Architecture

OpenSource Ortho mobile is a phone-friendly companion to the browser/Python
workspace, not a second full treatment-planning engine.

## Why Mobile Is STL-First

Modern phones can handle meaningful geometry work, especially STL metadata,
preview rendering, simple transforms, and small review packages. The full repo,
however, depends on heavier and more auditable workflows for segmentation,
registered per-tooth meshes, print package generation, and CBCT/DICOM review.

For that reason, iOS and Android allow mobile fallback generation only for
STL-only cases:

- The app asks the engine first.
- If the engine is offline and every selected record is an STL, the app may
  synthesize a `mobile-stl-best-effort` review.
- That review is explicitly caveated as STL metadata only.
- It routes segmentation, mesh-backed edits, CBCT/DICOM, root/bone checks, and
  print-critical review to the browser/full engine.

CBCT/DICOM and photos can be attached on mobile as records and context, but they
do not enable offline mobile synthesis. Root/bone work needs local DICOM
ingestion, volume viewing, STL-to-CBCT registration, reviewed anatomy, and
quality metrics. A phone may eventually help display or annotate those records,
but it should not silently claim to perform the full root/bone-aware workflow.

## Real scan viewing

The Teeth tab defaults to USER_ONE's observed baseline and week-7 scan history.
Both apps render every STL triangle (SceneKit on iOS, OpenGL ES on Android), with
both arches together, a continuous baseline/week-7 reveal slider, rotation,
zoom, and reset. The slider reveals recorded surfaces without morphing vertices. Sample viewing stays
separate from the uploaded case and plan generation. No synthetic teeth or
inferred intermediate stages are shown. Full originals are copied from the UUID
dataset at build time, with SHA-256 verification at load; they are not duplicated
in the source tree. The top-bar history remains a timeline with fixed PNG views.

The views fit each arch independently and do not measure tooth movement. The
progress scan's units and registration remain unverified. See
[mobile build details](../mobile/README.md),
[format support and limits](../mobile/SCAN_IMPORT.md), and the
[post-implementation audit](MOBILE_AUDIT_2026-09-22.md).

## Browser Handoff

The browser/Python workspace remains the source of truth for high-fidelity work:

- STL registration into the mesh workspace
- auto/manual segmentation into per-tooth meshes
- CBCT/DICOM ingestion, registration, reviewed anatomy, and root/bone-aware
  checks
- deterministic generation and correctness checks
- print package generation from engine outputs
- versioned case review and plan changes

Mobile can import JSON produced by that workspace and store it as an opaque
review/package artifact. The device copy is useful for review, sharing, and
handoff, but edits still happen in the browser/full engine.

## Current Implementation

Both native apps share the same policy:

- `SelectedScan` supports STL intake for mobile generation.
- The upload screens preview STL, OBJ, PLY, ASC, XYZ, and PTS locally and accept
  CBCT/DICOM attachments, photo-library images,
  Files/iCloud/Drive-style photo providers, and browser review JSON.
- `OnDevicePlanSynthesizer` creates a limited response only for STL-only inputs.
- `StoredPlanReview` holds browser-generated JSON without interpreting or
  mutating it.
- The primary review preview renders selected scan geometry locally when file
  bytes/URI access is available; CBCT/DICOM is attached but still requires the
  browser/full engine for volume rendering.
- The Review screen shows mobile warnings and stored browser reviews.
- The Print/Send step includes selected scans, the generated result, stored
  browser reviews, and the standing safety disclaimer in the exported JSON.

## Progress Tracker

- Done: iOS and Android STL-only on-device fallback.
- Done: iOS and Android browser-review JSON import.
- Done: iOS and Android photo/CBCT attachment intake.
- Done: iOS and Android scan-backed STL preview in the Generate/Teeth step.
- Done: expanded mobile glossary and browser-style mouth map work.
- Done: shared docs and API contract language for the mobile boundary.
- Done: browser/full-engine canonical root/bone fixture for the Sample Test Case
  (mobile may import its review JSON, but does not synthesize that workflow).
- Next: durable on-device review library with rename/delete.
- Next: engine-backed STL byte registration from mobile.
- Next: case handoff link/QR/deep-link between browser workspace and device.
- Next: per-tooth mesh preview using `GET /api/mesh/<id>` after segmentation.
- Later: CBCT/DICOM display or annotation in mobile only after it can preserve
  the browser/full-engine registration, reviewed-anatomy, quality, and privacy
  contracts.

## Safety Rule

Mobile verdict labels and generated packages must never say a plan is safe,
approved, cleared, complete, suitable, or ready for treatment. A mobile
`CONSISTENT` label means only that the lightweight artifact is internally
consistent with the fields the app has available.
