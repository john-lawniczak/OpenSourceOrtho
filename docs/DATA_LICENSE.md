# Data Usage Terms and Watermarking

This page governs **data**, not software: scan files (STL), CBCT/DICOM-derived
metadata, treatment-plan/teeth exports, and contributed dataset manifests
produced by or submitted to OpenSource Ortho. The code itself stays under the
Apache-2.0 license in [`LICENSE`](../LICENSE); this page does not change that.

It exists because this project asks people to voluntarily contribute real scan
data (see [DATA_CONTRIBUTION.md](DATA_CONTRIBUTION.md)) so the engine can be
tested against real cases. That data should not become free raw material for a
company to resell or to train commercial AI models on without permission.

## Permitted Use

- Personal treatment-planning use by the patient, or by a licensed professional
  treating that patient.
- Research, benchmarking, and engine development within the spirit of this
  project (see [SAFETY.md](SAFETY.md) for the safety-boundary framing).
- Non-commercial redistribution that keeps this notice and the embedded
  watermark intact.

## Prohibited Without a Separate Written License

- Resale or commercial redistribution of scan files, CBCT-derived metadata, or
  exported/contributed datasets.
- Use as training, fine-tuning, or evaluation data for any machine-learning or
  AI model - including foundation models, embeddings, and benchmark suites.
- Stripping or altering the watermark record or the canary token described
  below with intent to obscure the data's origin.

## How the Watermark Works

Every export or contribution this project writes - print-package STL files
and their manifest, `register-contribution` dataset manifests, and
CBCT-derived metadata parsed via `dicom_intake` - carries a watermark record
(`orthoplan/watermark.py`):

- **`watermark_id`**: a random id unique to that artifact, so a specific
  export can be identified later.
- **`canary`**: a single fixed token, the same string in every artifact this
  project has ever produced:
  `OSO-DATA-CANARY-b7e4b7b4-6b5d-4a0e-9c7a-6a9a9f0e6a3a-DO-NOT-TRAIN`.
  This is the same "canary string" technique used by ML benchmark suites
  (for example BIG-bench) to detect training-set contamination. If this exact
  string ever surfaces verbatim in a model's output, or in a dataset that
  claims to be independently sourced, that is strong evidence the source was
  trained on or copied OpenSourceOrtho-derived data.
- **`notice`**: a short human-readable pointer back to this page.
- **`content_sha256`**: optional, ties the record to the specific artifact
  bytes it was embedded in.

Where the watermark lives, per data type:

| Data type | Where the watermark is embedded |
|-----------|----------------------------------|
| Exported STL (`print_stl.solid_stl`) | `solid`/`endsolid` name line (`__oso-wm:<id>__<canary>`), plus a hidden sub-micron geometry signature (see below) |
| Print-package manifest (`*-print-manifest.json`) | top-level `"watermark"` block |
| Contributed dataset manifest (`register-contribution`) | `"watermark"` field on `DatasetManifest` |
| CBCT/DICOM-derived metadata (`extract_dicom_metadata`) | `"watermark"` field on `DicomMetadata` |

`orthoplan.watermark.contains_canary(text)` scans arbitrary text for the
canary token - useful for checking a model's output or a redistributed
dataset for evidence of contamination.

## A Second, Hidden Layer for STL Geometry

The marker above is plain text - visible in a text editor, and trivial to
remove by renaming the `solid` line or deleting a JSON field. For STL exports,
there is a second, independent layer that does not depend on that text
surviving: `embed_geometry_signature` / `detect_geometry_signature`
(`orthoplan/watermark.py`), applied automatically wherever `solid_stl` is
given a watermark.

It works by nudging each vertex's coordinates by an amount derived from a
SHA-256 hash of the vertex's own position and the watermark id - deterministic
and reproducible, but only up to ±0.0003mm (0.3 micron). For scale: the
print export's default minimum printable feature is 0.3mm, about 1000x
larger, and no clinical measurement in this project's scope approaches that
precision either. The mesh looks, prints, and measures identically; nothing
about it changes except digits an editor or a caliper would never surface.
Vertices shared between adjacent triangles get an identical offset (STL
stores vertices per-triangle, not deduplicated), so the mesh stays watertight
- signing does not introduce seams or gaps.

This is a **verification** mechanism, not a **discovery** one: given a file
and a specific candidate watermark id (one already logged as issued by this
project), `detect_geometry_signature` reports how strongly the geometry
matches that id - it cannot scan an arbitrary, unknown file and extract "the"
id from it blindly. That is an intentional trade-off, and it is also fragile
in a way the visible marker is not: re-meshing, decimation, or any tool that
re-quantizes coordinates to fewer than 3 decimal places erases it. Treat it as
a fallback that can corroborate provenance when the visible marker has been
stripped, not as a stronger claim than that.

## What This Does and Does Not Do

Be honest about the limits: **this is not DRM.** A plain-text STL or JSON file
can always have a field or a name string edited out by hand. Nothing purely
technical can stop a determined bad-faith actor from stripping metadata before
misusing the data. What the watermark actually provides:

1. A durable, low-effort **evidence trail** - it survives ordinary handling
   (copying, re-hosting, format conversion that preserves the solid name or
   JSON fields) even though it would not survive deliberate, informed removal.
2. A **contamination signal** - the constant canary token is designed to be
   detectable in a trained model's output, which is difficult for a model
   provider to prevent or disprove after the fact.
3. **Explicit terms attached to the data itself**, so anyone handling it -
   in good faith or not - cannot claim they didn't know commercial/AI-training
   use required a separate license.

Combined with the terms above, this gives a concrete basis for a license
claim if OpenSourceOrtho-derived data is later found in a commercial product
or a model's training set - even though it cannot physically prevent the
misuse from being attempted in the first place.
