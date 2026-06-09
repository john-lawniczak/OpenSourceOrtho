# CBCT/DICOM Planning Roadmap

> Status: planned. No CBCT/DICOM parser, volume viewer, segmentation model, or
> STL-to-CBCT registration pipeline is shipped yet.

OpenSource Ortho's product direction is treatment-planning software for clear
aligner workflows, including accurate staged geometry for users who want to
manufacture aligners. STL-only planning remains a first-class path, but it is
surface-based: it sees visible crown geometry only. CBCT/DICOM support is the
higher-fidelity path for root/bone-aware planning.

This roadmap exists so CBCT work is built deliberately instead of as a
half-implemented "full evaluation pipeline." A CBCT record can improve planning,
but only if ingestion, registration, segmentation, validation, and manufacturing
handoff are treated as product-critical systems.

## Planning Tiers

### Surface Plan: STL Only

STL-only users should still get a strong planning workflow:

- intraoral STL import and scale confirmation
- crown segmentation and per-tooth staged movement
- arch-form and spacing/crowding proposals
- crown-surface collision checks
- attachment/IPR intent tracking
- staged model or manufacturing package export
- clear data-gap findings for roots, bone, periodontal status, and occlusion

This tier must never imply that root position, alveolar bone limits, periodontal
support, impacted teeth, nerves, airway, pathology, or biological response were
assessed. It is a surface-based plan.

### Enhanced Records Plan: STL Plus Photos/X-rays/Notes/Occlusion

Additional records can add context and close specific data gaps, but most are not
3D root/bone geometry. They should improve review, handoff questions, and
provenance without pretending to be volumetric planning.

### Root/Bone-Aware Plan: STL Plus CBCT/DICOM

CBCT/DICOM can unlock the highest-fidelity planning tier when the app can:

- ingest and display the local DICOM volume
- register the intraoral STL surface to the CBCT volume
- segment or import crowns, roots, and alveolar bone with reviewable confidence
- derive trusted tooth axes and root geometry
- run root/bone-aware constraints and visualization
- preserve provenance and quality metrics for every derived object

CBCT should be recommended or required only when the planned movement or case
complexity exceeds what surface data can responsibly support. It should not be a
universal prerequisite for every STL-only workflow.

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

Segmentation models, weights, and datasets require the same license discipline as
the learned crown segmenter: code license, weight license, and dataset license are
separate. Do not commit third-party patient volumes, model weights, or datasets
without explicit permission and a reviewed license.

## Phase 5: Root/Bone-Aware Planning

Goal: let planning consume trusted CBCT-derived anatomy as constraints, not as
silent approval.

Potential checks:

- renderable tooth axes from trusted root/crown anatomy
- root proximity and inter-root collision warnings
- cortical boundary proximity warnings
- root/bone context for tip, torque, intrusion, extrusion, and expansion
- "cannot assess" findings when registration or segmentation quality is missing
- tooth-specific constraints derived from reviewed anatomy

The verdict vocabulary should remain limited to internal consistency terms such
as `CONSISTENT` / `ISSUES` / `NOT_APPLICABLE` unless the project establishes a
separate clinical/regulatory approval workflow.

## Phase 6: Manufacturing Handoff

Goal: produce the most accurate manufacturing package the available data can
support.

The STL-only and CBCT-enhanced paths can both export staged geometry, but the
manifest must label the planning tier and data limitations.

Manufacturing-specific work includes:

- staged model geometry from actual per-tooth meshes when available
- direct aligner geometry only after trimline, blockout, attachment, material
  thickness, and manufacturing compensation are defined
- print orientation, material, post-processing, and fit-check metadata
- deterministic hashes tying outputs to inputs, transforms, engine version, and
  plan findings

The software can generate reproducible files, but intraoral use depends on
validated materials, fabrication process controls, professional supervision, and
the user's regulatory obligations.

## Acceptance Gates

Before CBCT-derived data affects movement planning:

- DICOM parser and viewer are optional and local-only
- PHI handling is documented and tested
- STL-to-CBCT registration has explicit quality output
- anatomy segmentation is reviewable and provenance-bound
- root/bone-aware checks have deterministic tests
- at least one validation harness exists for registration and segmentation quality
- UI copy distinguishes STL-only, enhanced-records, and root/bone-aware plans
- generated files label the planning tier and unresolved data gaps

## Implementation Ownership

- `orthoplan/io/`: DICOM metadata and volume import adapters
- `orthoplan/model/`: CBCT record, registration, and derived-anatomy data models
- `orthoplan/evaluation/`: deterministic data-gap and root/bone-aware findings
- `orthoplan/planning/`: only consumes trusted, reviewed geometry contracts
- `orthoplan/viz/` and `ui/`: viewer and display contracts
- `docs/`: product boundary, validation, and manufacturing documentation

The guiding rule: STL-only plans should be useful and polished, while CBCT/DICOM
should unlock a higher-fidelity tier only when the data and derived anatomy are
good enough to support that feature.
