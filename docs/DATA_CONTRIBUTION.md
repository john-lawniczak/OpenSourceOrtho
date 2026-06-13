# Contributing Data

OpenSource Ortho improves as more real scans and results are tested against the
engine. You can help by contributing privacy-safe case bundles: scans, plan
intent, refinements, and outcomes that can be compared over time. This page
explains **what to contribute, how identity tracking works, and the privacy rules
that are enforced in code.**

> Contributing data is voluntary. Only contribute scans you have the right to
> share, and only after removing patient-identifying information. See
> [SAFETY.md](SAFETY.md).

## What Helps

For a general user, the most helpful contributions are, from most to least useful:

1. **Before-and-after STL scans**: upper and lower scans from before treatment
   and after treatment, ideally from the same scanner/export format. This is the
   best evidence for what actually changed.
2. **Progress or refinement scans**: any mid-treatment scan, refinement scan, or
   scan taken when trays stopped tracking. These help measure where a plan drifted
   from reality.
3. **The intended plan in a non-proprietary form**: an OpenSource Ortho plan JSON,
   a hand-entered summary, or notes listing stage count, wear interval, which
   teeth moved, attachments, IPR/spacing, locked teeth, and movement exclusions.
4. **Outcome notes**: whether refinements were needed, whether trays tracked, what
   changed mid-treatment, scanner model, scan units, and known scan quirks -
   **without** patient identity.
5. **Initial STL scans only**: still useful for segmentation, scale, mesh-quality,
   and arch-form benchmarks, but they cannot teach outcome prediction by
   themselves.
6. **Reviewed CBCT/DICOM-derived anatomy**: useful for root/bone-aware benchmarks
   only when a licensed professional ordered/interpreted the record, PHI has been
   removed, and you have the right to share it.
7. **Synthetic or consented teaching fixtures** with known labels or landmarks.

Do not contribute proprietary treatment-planning files, screenshots, assets, or
exports unless you are certain the license allows redistribution. When in doubt,
contribute your own scan files plus an OpenSource Ortho plan JSON instead.

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

Use the CLI to create the id. Do not invent an id from a name, initials, email,
birth date, appointment date, chart number, or scanner-office label. Once a case
has an id, keep that same id for later final/progress/refinement scans from the
same case so the longitudinal record stays connected.

## Case Bundle Standard

Put each contributed case in one folder. The folder name should be the generated
specimen id whenever possible:

```text
datasets/
  spec-<uuid>/
    manifest.json
    initial-upper.stl
    initial-lower.stl
    initial-bite.stl              # optional
    progress-01-upper.stl         # optional
    progress-01-lower.stl         # optional
    refinement-01-upper.stl       # optional
    refinement-01-lower.stl       # optional
    final-upper.stl
    final-lower.stl
    plan-summary.json             # optional but strongly preferred
    outcome-notes.md              # optional, no PHI
```

Use these filename labels so future tooling can parse the case consistently:

| Label | Meaning |
|-------|---------|
| `initial-upper.stl` / `initial-lower.stl` | Pre-treatment upper/lower scans. |
| `initial-bite.stl` | Optional bite or occlusion scan from the starting records. |
| `progress-01-upper.stl` / `progress-01-lower.stl` | Mid-treatment scan pair; increment the number for later progress records. |
| `refinement-01-upper.stl` / `refinement-01-lower.stl` | Scan pair taken for a refinement or restart; increment the number for later refinements. |
| `final-upper.stl` / `final-lower.stl` | Post-treatment or latest available result scan pair. |
| `plan-summary.json` | Non-proprietary summary of intended movement and controls. |
| `outcome-notes.md` | Plain-language, non-identifying notes about tracking/refinements/results. |

If you only have one scan pair, use `initial-upper.stl` and `initial-lower.stl`.
If you only have one arch, keep the same label style (`initial-upper.stl`, for
example) and say what is missing in `outcome-notes.md`.

## Plan Summary Standard

When you do not have an OpenSource Ortho plan JSON, add a simple
`plan-summary.json`. Keep it non-proprietary and patient-anonymous:

```json
{
  "schema": "opensource-ortho-plan-summary-v1",
  "stage_count": 24,
  "wear_interval_days": 7,
  "arches_treated": ["upper", "lower"],
  "moved_teeth": ["11", "12", "21", "22"],
  "attachments": ["11", "21"],
  "ipr_contacts": [
    {"between": ["11", "21"], "amount_mm": 0.2}
  ],
  "locked_teeth": ["16", "26"],
  "notes": "No names, dates of birth, email, phone, record numbers, or clinic identifiers."
}
```

Useful fields, from most to least important:

- `stage_count`
- `wear_interval_days`
- `arches_treated`
- `moved_teeth`
- `attachments`
- `ipr_contacts`
- `spacing_contacts`
- `locked_teeth`
- `movement_exclusions`
- `refinement_count`
- `tracking_notes`

Approximate values are better than silence when they are clearly labeled. Do not
copy proprietary plan files, screenshots, or branded exports into the dataset.

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
  `sha256`, vertex/face counts, bounds, role, sequence, and arch labels,
  generates a fresh `spec-…` id, and writes a manifest. It never copies or
  uploads mesh bytes.
- Standard filenames such as `initial-upper.stl`, `progress-01-lower.stl`, and
  `final-upper.stl` are parsed automatically into per-file role/arch labels.
- `--plan-summary` validates and embeds a non-proprietary
  `opensource-ortho-plan-summary-v1` summary in the manifest.
- `--outcome-notes` records the notes filename and SHA-256 hash after rejecting
  obvious PHI field markers in the text.
- Output is local. Sharing the dataset (e.g. a pull request or a data drop) is a
  separate, deliberate step you take.

For a longitudinal case bundle, register all STL files together so one manifest
records the complete set:

```bash
orthoplan register-contribution \
  datasets/spec-<uuid>/initial-upper.stl \
  datasets/spec-<uuid>/initial-lower.stl \
  datasets/spec-<uuid>/final-upper.stl \
  datasets/spec-<uuid>/final-lower.stl \
  --units mm \
  --i-confirm-no-phi \
  --notes "before/after scan pair; no PHI" \
  --out datasets/spec-<uuid>/manifest.json
```

## Manifest Schema

| Field | Meaning |
|-------|---------|
| `specimen_id` | `spec-<uuid4 hex>` stable handle |
| `created_at` | UTC registration time |
| `engine_version` | engine version at registration |
| `scans[]` | per-file: `filename` (redacted), `role`, `sequence_index`, `sha256`, `units`, `provenance`, `arch`, `vertex_count`, `face_count`, `bounds` |
| `plan_summary` | optional validated non-proprietary plan summary |
| `plan_summary_filename` | optional redacted sidecar filename |
| `outcome_notes_filename` | optional redacted sidecar filename |
| `outcome_notes_sha256` | optional content hash for outcome notes |
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

Before opening a pull request or sending a data drop, check:

- The folder is named `spec-<uuid>` or the manifest contains the canonical
  `specimen_id`.
- Every STL uses the standard role/arch filename labels.
- `manifest.json` was generated by the CLI and includes SHA-256 hashes.
- Any `plan-summary.json` or `outcome-notes.md` contains no names, dates of
  birth, appointment dates, email addresses, phone numbers, addresses, clinic
  names, chart numbers, or other identifiers.
- You have the right to share the files under the repository's contribution
  terms.

## Benchmark Use

The validation benchmark reads these manifests and reports a `longitudinal-data`
component with readiness metrics for:

- target setup benchmarks: initial upper/lower scan pairs
- tracking-error benchmarks: initial plus final upper/lower scan pairs
- refinement-prediction benchmarks: progress/refinement scans or a nonzero
  `refinement_count` in `plan-summary.json`

For consented longitudinal bundles, `longitudinal_outcome_reports()` also emits
numeric bounds-centroid proxy reports:

- target-setup error: initial scan bounds compared with final or refinement scan
  bounds per arch
- tracking error: initial scan bounds compared with progress scans only when
  stage timing is known
- refinement prediction: planned refinements separated from unplanned observed
  refinements and missing/unknown outcomes

These are readiness, corpus-coverage, and geometry-proxy metrics, not clinical
performance claims. Sparse community data must not be described as clinical
accuracy; it only shows whether the open dataset is becoming useful for future
target setup, tracking, and refinement studies.
