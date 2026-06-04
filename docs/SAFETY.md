# Safety Boundary

OpenSource Ortho is a research and development toolkit for geometric planning workflows. It is not distributed as medical device software and is not intended to provide diagnosis, treatment approval, or autonomous clinical decision-making.

## Capability Boundary

OpenSource Ortho may describe:

- what data was provided
- what proposed movement values exist in a plan
- whether those values exceed user-configured caps
- whether stages are internally inconsistent
- what clinically relevant data is unavailable
- what questions a clinician may need to answer

OpenSource Ortho must not state or imply:

- a plan is safe, approved, cleared, clinically acceptable, or ready for treatment
- a patient is a good candidate for aligners
- roots, bone, periodontal structures, pathology, or airway status are acceptable when those data are unavailable
- a movement threshold is authoritative unless it is either user-configured or cited

## Geometry, Not Biomechanics

OpenSource Ortho models crown-surface geometry only. It does not model force levels,
anchorage, attachment or IPR mechanics, tooth-movement feasibility, or root-resorption
risk. A proposed movement that fits within configured caps is a geometric statement, not a
biomechanical or clinical one. Visualization pivots (crown centroid) are explicit display
assumptions and never imply knowledge of root or bone position.

Per-tooth local frames (`ToothLocalFrame`) derived from crown-surface PCA are approximate
metadata only: their axes are ordered by geometric variance, not anatomy, and they do not
represent mesiodistal/buccolingual/long axes or root direction. PCA frames do not authorize
rotation rendering. Rotation is renderable only when the engine receives a non-approximate,
trusted anatomical frame or a global frame with resolved anatomical axes.

## Privacy Posture

Intraoral STL scans are patient-derived data. The toolkit:

- never stores mesh bytes in serialized plans; only redacted asset metadata is kept
- strips directory structure and rejects absolute paths and parent-directory traversal,
  because clinical export paths routinely embed patient names or DOB
- treats scan units as unverified until the user confirms them

Retention and deletion guarantees are out of scope for Phase 1 and are the responsibility of
the deploying party; this is noted here so it is not mistaken for a solved problem.

## LLM Boundary

Model-generated findings are untrusted advisory text. `lint_finding()` is the single safety
gate: it is enforced as a pipeline stage, not at object construction, so a malformed model
finding is rejected and quarantined rather than crashing the pipeline. Use
`quarantine_findings()` for batches of untrusted findings.

The gate enforces that:

- verdict language is scanned across ALL text fields (title, message, data gap, clinician
  question, reference), with word-boundary matching so negated forms (e.g. "unsafe") are not
  falsely flagged and positive-sounding clearances (e.g. "good candidate", "within normal
  limits") are caught
- model-sourced `mechanics` findings are forbidden; deterministic rules own mechanics. Models
  may comment on data gaps, education, or clinician questions only
- warning findings must include both a data gap and a clinician question
- mechanics findings must reference a configured cap or citation

Every model-sourced finding must also carry model provenance, remain observational and
conditional, include data gaps when relevant, and avoid invented thresholds.

## Regulatory Note

This document is not legal advice. Anyone using or modifying this project for clinical workflows is responsible for professional, legal, privacy, and regulatory obligations in their jurisdiction.
