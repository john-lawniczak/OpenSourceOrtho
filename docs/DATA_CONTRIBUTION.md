# Contributing Data

OpenSource Ortho improves as more real scans and results are tested against the
engine. You can help by contributing STL scans and the plans/results you produced
from them. This page explains **what to contribute, how identity tracking works,
and the privacy rules that are enforced in code.**

> Contributing data is voluntary. Only contribute scans you have the right to
> share, and only after removing patient-identifying information. See
> [SAFETY.md](SAFETY.md).

## What Helps

- **STL intraoral/surface scans** (upper, lower, or both arches).
- **Plan JSON** exported from the app for those scans.
- **Evaluation/report JSON** so engine output can be compared over time.
- Notes about scanner, units, and any known quirks - **without** patient identity.

## Privacy Posture (enforced, not just advised)

Identity is a random UUID, never anything derived from the patient. The manifest
model (`orthoplan/model/dataset.py`) enforces this:

- Mesh **bytes are never stored** in the manifest - only redacted metadata.
- File references are reduced to a **basename** (`redact_reference`), because
  directory paths commonly embed patient names.
- The manifest model uses `extra = "forbid"`, so a stray `patient_name`/`dob`/
  `email`/`mrn`/`ssn` key is **rejected**, not silently stored.
- `notes` are scanned for identifying-field markers and rejected if present.

There are **no** name, date-of-birth, contact, or record-number fields anywhere
in the schema - this is locked by a test (`tests/test_dataset.py`).

## Specimen IDs

Each contributed dataset gets a stable, non-identifying **specimen id** of the
form `spec-<uuid4 hex>`. This is how data is tracked and deduplicated as the
collection grows. The first tracked specimen is the bundled OrthoCAD example at
[`ui/example-scans/canonical-orthocad-001/manifest.json`](../ui/example-scans/canonical-orthocad-001/manifest.json).

## Register a Contribution

```bash
orthoplan register-contribution path/to/upper.stl path/to/lower.stl \
  --arch maxillary --units mm \
  --i-confirm-no-phi \
  --out datasets/<your-folder>/manifest.json
```

- `--i-confirm-no-phi` is **required**: it asserts the files and notes contain no
  patient-identifying information. Without it, nothing is written.
- The command inspects each STL (via `io/stl_import.py::inspect_stl`), records
  `sha256`, vertex/face counts, and bounds, generates a fresh `spec-…` id, and
  writes a manifest. It never copies or uploads mesh bytes.
- Output is local. Sharing the dataset (e.g. a pull request or a data drop) is a
  separate, deliberate step you take.

## Manifest Schema

| Field | Meaning |
|-------|---------|
| `specimen_id` | `spec-<uuid4 hex>` stable handle |
| `created_at` | UTC registration time |
| `engine_version` | engine version at registration |
| `scans[]` | per-file: `filename` (redacted), `sha256`, `units`, `provenance`, `arch`, `vertex_count`, `face_count`, `bounds` |
| `consent_acknowledged` | you confirmed you may share this data |
| `phi_removed` | you confirmed PHI was removed |
| `notes` | optional, non-identifying notes |

## Directory Convention

Keep each contributed dataset in its own folder with a `manifest.json`:

```text
datasets/
  spec-<uuid>/           # or a human-readable slug; the manifest holds the UUID
    upper.stl
    lower.stl
    manifest.json
```

The bundled example keeps the readable folder name `canonical-orthocad-001` and
carries its specimen id inside `manifest.json`; the folder name is a convenience
alias, the UUID is the canonical identity.
