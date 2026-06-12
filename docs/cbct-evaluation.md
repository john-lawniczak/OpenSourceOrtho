# CBCT/DICOM Safety-Review Roadmap

> Status: in progress. Local DICOM metadata intake, 3D Slicer handoff,
> review-gated registration proposals, and local sparse-mask root/bone proposals
> are shipped. Raw-volume proposals now include connected-component cleanup,
> field-boundary truncation flags, centerline/voxel quality metrics, and
> synthetic fail-closed benchmarks. A full clinical-grade segmentation model and
> volume viewer remain out of scope for the core install.

## Local DICOM metadata intake (shipped)

Install the optional extra to enable metadata parsing:

```
pip install opensource-ortho[dicom]   # pulls pydicom
```

`orthoplan.dicom_intake.parse_dicom_metadata` reads ONLY structural acquisition
fields (modality, voxel spacing, dimensions, orientation, study date) via
`pydicom` with `stop_before_pixels=True`. Patient identifiers (name, id, birth
date, accession, referring physician, institution) are never copied into the
`DicomMetadata` model - see `PHI_TAGS_EXCLUDED`. Volume pixel bytes are never
loaded into plan JSON; the file stays in the local record workspace and is opened
in a trusted local viewer (3D Slicer) via `cbct_handoff`. When the extra is not
installed, intake fails closed (returns an error) rather than guessing.

CBCT lifecycle status (`unavailable` -> `attached` -> `registered` ->
`anatomy-reviewed`) is fail-closed: an attachment stays `attached` until accepted
registration and reviewed anatomy exist, and a CBCT attachment never changes
movement generation on its own.

OpenSource Ortho's product direction is a safety-boundary-first clear-aligner
planning playground and research toolkit. It can model staged geometry and
produce manufacturing-oriented exports, but it does not claim to produce a
complete treatment plan and any physical use is the user's own responsibility
and risk. STL-only planning remains a first-class exploratory path, but it is
surface-based: it sees visible crown geometry only. CBCT/DICOM support is the
higher-fidelity record path for root/bone-aware checks.

This roadmap exists so CBCT work is built deliberately instead of as a
half-implemented "full evaluation pipeline." A CBCT record can improve the
available checks, but only if ingestion, registration, segmentation, validation,
and manufacturing handoff are treated as safety-critical systems. None of these
phases may imply clinical approval, treatment suitability, or readiness to wear
an appliance.

## Safety-Review Tiers

### Surface Review: STL Only

STL-only users should still get a strong exploratory workflow:

- intraoral STL import and scale confirmation
- crown segmentation and per-tooth staged movement
- arch-form and spacing/crowding proposals
- crown-surface collision checks
- attachment/IPR intent tracking
- staged model or manufacturing-oriented package export
- clear data-gap findings for roots, bone, periodontal status, and occlusion

This tier must never imply that it is a complete treatment plan or that root position, alveolar bone limits, periodontal
support, impacted teeth, nerves, airway, pathology, or biological response were
assessed. It is a surface-based review.

### Enhanced Records Review: STL Plus Photos/X-rays/Notes/Occlusion

Additional records can add context and close specific data gaps, but most are not
3D root/bone geometry. They should improve review, handoff questions, and
provenance without pretending to be volumetric planning or clinical clearance.

### Root/Bone-Aware Review: STL Plus CBCT/DICOM

CBCT/DICOM can unlock the highest-fidelity review tier when the app can:

- ingest and display the local DICOM volume
- register the intraoral STL surface to the CBCT volume
- segment or import crowns, roots, and alveolar bone with reviewable confidence
- derive trusted tooth axes and root geometry
- run root/bone-aware checks and visualization
- preserve provenance and quality metrics for every derived object

CBCT should be recommended or required only by the workflow's configured safety
rules or by a responsible reviewer when the movement or case context exceeds what
surface data can responsibly support. It should not be a universal prerequisite
for every STL-only workflow, and its presence alone must not imply a complete
treatment plan.

## Phase 1: Contract And Ingestion

Goal: attach CBCT/DICOM records to a case without changing planning behavior.

- Add a DICOM/CBCT record model with modality, study metadata, provenance, and
  local file references. Serialized plans should not contain volume bytes.
- Add optional DICOM parsing behind an extra such as `dicom`, keeping the core
  install light.
- Redact paths and identifiers aggressively. DICOM files can contain PHI in
  metadata, filenames, and nested tags.
- Add a local-only upload/registration contract for the browser/server boundary.
- Surface `cbct=True` only when a record is actually attached and acknowledged.

Non-goals:

- no automated diagnosis
- no root/bone clearance
- no movement changes from CBCT data
- no claim that the volume has been interpreted

## Phase 2: On-Device Volume Viewer

Goal: let users and reviewers inspect the record locally.

- Add axial/coronal/sagittal slice viewing or hand off to a trusted local viewer.
- Show study/date/provenance and whether the volume is registered to an STL.
- Keep viewer code separate from planning and evaluation logic.
- Prefer optional 3D Slicer / VTK / pydicom integration paths rather than making
  heavy medical-imaging dependencies mandatory.

## Phase 3: STL-To-CBCT Registration

Goal: align the intraoral crown surface to the CBCT coordinate space with
explicit quality metrics.

- Define a `RegistrationTransform` contract: source asset, target volume,
  transform matrix, method, operator/model provenance, quality score, and notes.
- Support manual/imported transforms before automatic registration.
- Never silently assume the STL and CBCT are aligned.
- Do not let planning consume CBCT anatomy unless registration quality is present
  and acceptable for that feature.

## Phase 4: Reviewable Anatomy Segmentation

Goal: represent CBCT-derived anatomy as explicit, editable objects.

Candidate objects:

- root meshes or root centerlines per tooth
- crown/root combined tooth solids
- alveolar bone surface or boundary volumes
- mandibular canal/nerve paths when in scope
- sinus/airway surfaces when in scope

Every derived object needs:

- source record and registration provenance
- model/operator provenance
- confidence or quality metadata
- review/correction status
- clear handling for missing, uncertain, or out-of-field anatomy

Current local sparse-mask proposals satisfy this contract by keeping every object
`PROPOSED`, filtering tiny disconnected root components, flagging masks that
touch the CBCT field boundary as out-of-field, and recording quality metrics such
as voxel counts, component counts, retained/dropped components, centerline length,
and boundary voxel counts. These metrics are review aids only; they do not make
raw-volume anatomy trusted without human acceptance/correction.

Segmentation models, weights, and datasets require the same license discipline as
the learned crown segmenter: code license, weight license, and dataset license are
separate. Do not commit third-party patient volumes, model weights, or datasets
without explicit permission and a reviewed license.

## Phase 5: Root/Bone-Aware Checks

Goal: let the engine consume trusted CBCT-derived anatomy as constraints and
warnings, not as silent approval or a complete treatment plan.

Potential checks:

- renderable tooth axes from trusted root/crown anatomy
- root proximity and inter-root collision warnings
- cortical boundary proximity warnings
- root/bone context for tip, torque, intrusion, extrusion, and expansion
- "cannot assess" findings when registration or segmentation quality is missing
- tooth-specific constraints derived from reviewed anatomy

The verdict vocabulary must remain limited to internal consistency terms such as
`CONSISTENT` / `ISSUES` / `NOT_APPLICABLE`. It must not become "safe",
"approved", "ready", "clinically acceptable", or equivalent clearance language.

## Phase 6: Manufacturing Handoff

Goal: produce a reproducible manufacturing-oriented package from the available
data while preserving every limitation and user-responsibility warning.

The STL-only and CBCT-enhanced paths can both export staged geometry, but the
manifest must label the review tier, data limitations, and unresolved risks.

Manufacturing-specific work includes:

- staged model geometry from actual per-tooth meshes when available
- direct aligner geometry only after trimline, blockout, attachment, material
  thickness, and manufacturing compensation are defined
- print orientation, material, post-processing, and fit-check metadata
- deterministic hashes tying outputs to inputs, transforms, engine version, and
  plan findings

The software can generate reproducible files, but it does not authorize wearing
or using an appliance. Intraoral use depends on validated materials, fabrication
process controls, professional supervision, and the user's own responsibility,
risk, and regulatory obligations.

## Acceptance Gates

Before CBCT-derived data affects any movement checks:

- DICOM parser and viewer are optional and local-only
- PHI handling is documented and tested
- STL-to-CBCT registration has explicit quality output
- anatomy segmentation is reviewable and provenance-bound
- root/bone-aware checks have deterministic tests
- at least one validation harness exists for registration and segmentation quality
- UI copy distinguishes STL-only, enhanced-records, and root/bone-aware plans
- generated files label the review tier, unresolved data gaps, and own-risk use

## Implementation Ownership

- `orthoplan/io/`: DICOM metadata and volume import adapters
- `orthoplan/model/`: CBCT record, registration, and derived-anatomy data models
- `orthoplan/evaluation/`: deterministic data-gap and root/bone-aware findings
- `orthoplan/planning/`: only consumes trusted, reviewed geometry contracts as
  exploratory constraints
- `orthoplan/viz/` and `ui/`: viewer and display contracts
- `docs/`: product boundary, validation, and manufacturing documentation

The guiding rule: STL-only reviews should be useful and polished, while
CBCT/DICOM should unlock a higher-fidelity safety-review tier only when the data
and derived anatomy are good enough to support that feature. No tier claims to be
a complete treatment plan or to make physical use safe.
