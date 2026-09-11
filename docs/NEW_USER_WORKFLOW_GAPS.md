# New-User Workflow Gaps

This document evaluates how well a new user can move from their own records to
an inspectable plan and manufacturing-oriented artifacts. Ratings describe
engineering and user-experience maturity for this safety playground and research
toolkit. They are not clinical-clearance, treatment-approval, manufacturing-fit,
or physical-use ratings.

## Current End-to-End Assessment

The complete first-time workflow is approximately **6.5/10** today. The engine,
safety boundaries, sample walkthrough, and stage-model export are stronger than
the ordinary-user journey with arbitrary real-world records.

| Journey area | Current | Main limitation |
|---|---:|---|
| Install and launch | ~6.5/10 | Comfortable for developers; no polished desktop installer or guided dependency repair for nontechnical users. |
| Upload STL records | ~8.0/10 | Shared metadata readiness report and action links exist; file verification, persisted quality evidence, and capability-specific gates remain incomplete. |
| Segment and review teeth | ~6.5/10 | Reviewable proposals exist; difficult real scans can still require substantial correction without brush/split/merge tools. |
| Attach and use CBCT/DICOM | ~5.0/10 | Metadata, registration, anatomy contracts, and gates exist; there is no complete drop-in volume-viewing and reviewed-segmentation workflow. |
| Build staged movement proposals | ~7.0/10 | Deterministic staging is substantial, but target quality depends heavily on reviewed inputs and does not establish biological suitability. |
| AI assistance | ~6.5/10 | Good explanation and consent boundaries; limited structured, diffable plan-action support. |
| Inspect movement in 3D | ~7.5/10 | Real meshes and stages render well; arbitrary-record correction and cross-modal review remain uneven. |
| Export printable stage models | ~8.0/10 | Reproducible manifests and geometry QA are strong within the software-only boundary. |
| Export aligner-shell geometry | ~5.5/10 | Optional shell generation and QA exist, but backend strength and real-record validation are limited. |
| Produce physically usable aligners | Not assessed | Printer calibration, materials, thermoforming, fit, forces, biocompatibility, and physical validation are outside this software. |

The ratings above intentionally distinguish **printable stage models** from
**aligner-shell geometry**. Neither is evidence that a physical appliance is
safe, suitable, correctly manufactured, or authorized for use.

## Priority Weak Areas

### 1. Unified Intake Readiness

The [initial shared readiness report](INTAKE_READINESS.md) now consolidates scan
metadata, segmentation links, bite declarations, CBCT attachments, registration
gates, and reviewed anatomy in the evaluation API and Review workspace. It
separates record evidence, plan checks, export prerequisites, and physical
validation, with links to the corresponding controls. The remaining work is to
extend that report beyond declared/persisted metadata to cover:

- which upper/lower STL files remain locally available and match their hashes
- units, orientation, scale plausibility, and arch identity
- whether a bite relationship is present or missing
- persisted segmentation quality-gate results alongside the existing review state
- CBCT/DICOM attachment, registration, and reviewed-anatomy state
- which planning, review, and export operations are currently unlocked
- the exact next action for every blocker

The report must distinguish record readiness, plan consistency, artifact
readiness, and physical validation rather than collapsing them into one verdict.

### 2. Segmentation Correction Workspace

Automatic segmentation is deliberately a proposal, but correction tools are too
limited for difficult scans. The UI needs reviewable operations for:

- splitting a merged crown region
- merging fragments
- brush/lasso reassignment
- hiding gingiva or scan artifacts
- visually marking missing teeth
- undo/redo and named reviewed versions
- before/apply comparison and per-tooth quality state

The goal is not silent automatic acceptance. It is lower review burden with a
clear provenance trail.

### 3. Practical CBCT Companion Workflow

The typed CBCT safety gates are ahead of the ordinary-user workflow. A practical
integration path should:

1. ingest a local DICOM directory with PHI-aware metadata handling
2. show what can and cannot be inspected in the browser
3. hand off to a trusted local viewer such as 3D Slicer when volume review is needed
4. import a documented reviewed-segmentation/landmark manifest
5. propose STL-to-CBCT registration with visible numeric quality
6. show cross-modal overlays for review
7. require explicit acceptance before anatomy becomes trusted

A bundled clinical-grade automatic CBCT segmenter is not implied by this path.
Caller-supplied masks and engineering fixtures must remain labeled accordingly.

### 4. Structured AI Proposals

The assistant is currently stronger at explanation than at auditable action.
Useful next actions include proposing, never silently applying:

- a lower configured movement cap
- holding or excluding selected teeth
- splitting movement across more stages
- grouping and explaining findings
- identifying missing records
- producing questions for a licensed professional

Every proposed action should carry structured JSON, a before/after diff,
provider/model/context provenance, deterministic re-evaluation, linted copy, and
explicit Apply/Reject controls. Model output remains untrusted.

### 5. Durable Case Lifecycle

The existing browser storage, versions, mesh workspace, and case records should
be unified into one recoverable case experience with:

- autosave and restart recovery
- named cases and last-opened state
- record hashes and local-storage location disclosure
- segmentation and plan versions
- audit history for edits, generation, comparison, and export
- portable backup/import
- schema migrations

### 6. Artifact Truth and Manufacturing Evidence

The UI and manifests should consistently separate:

- **record readiness** — required inputs are present and reviewed
- **plan consistency** — configured deterministic checks ran
- **artifact readiness** — exported geometry passed software-side QA
- **physical validation** — not evaluated by this software

Future validation should expand reviewed, license-compatible, non-PHI corpora for
messy scans, segmentation corrections, shell failures, and printer-profile
geometry deltas. Physical fit, material behavior, thermoforming, and clinical
authorization remain external responsibilities unless the project scope changes
and appropriate evidence exists.

### 7. Nondeveloper Distribution

The current local application is developer-friendly. Broader first-time use
would benefit from a signed desktop package or similarly controlled installer,
automatic dependency diagnostics, explicit local-data locations, schema/update
migrations, and optional installation of heavyweight mesh/CBCT components.

## Validation Needed

The bundled sample proves that the workflow can be exercised; it does not prove
performance on arbitrary records. Validation should cover multiple scanner
brands and cases with crowding, restorations, missing teeth, partial arches,
noisy gingiva, unusual orientation or scale, mixed record quality, and failed
shell inputs.

Release dashboards should track at least:

- record-intake failure and correction rates
- segmentation proposal quality and human correction time
- registration gate distributions
- deterministic finding counts by category
- export blocker frequency
- geometry-QA regression deltas
- recovery, migration, and case-roundtrip success

## Near-Term Definition of Done

The next meaningful new-user maturity milestone is reached when a user can load
their own upper/lower STL records, receive one actionable intake report, correct
and version segmentation, understand which review tier is active, inspect a
staged proposal, and export an artifact inventory whose limitations are
unambiguous. CBCT records should have an equally explicit local handoff/import
path. None of these steps may imply diagnosis, clinical approval, complete
treatment planning, manufacturing fit, or safe physical use.

Implementation work is tracked in [../TODO.md](../TODO.md).
