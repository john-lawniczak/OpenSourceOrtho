# Safety Boundary

OpenSource Ortho is a research and development toolkit for geometric planning workflows. It is not distributed as medical device software and is not intended to provide diagnosis, treatment approval, or autonomous decision-making.

## Capability Boundary

OpenSource Ortho may describe:

- what data was provided
- what proposed movement values exist in a plan
- whether those values exceed user-configured caps
- whether stages are internally inconsistent
- what interpretation-relevant data is unavailable
- what questions remain for handoff or follow-up

OpenSource Ortho must not state or imply:

- a plan is safe, approved, cleared, acceptable, or ready for treatment
- a patient is a good candidate for aligners
- roots, bone, periodontal structures, pathology, or airway status are acceptable when those data are unavailable
- a movement threshold is authoritative unless it is either user-configured or cited

## Geometry, Not Biomechanics

OpenSource Ortho models crown-surface geometry only. It does not model force levels,
anchorage, attachment or IPR mechanics, tooth-movement feasibility, or root-resorption
risk. A proposed movement that fits within configured caps is a geometric statement, not a
biomechanical one. Visualization pivots (crown centroid) are explicit display
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
  because export paths can embed patient names or DOB
- treats scan units as unverified until the user confirms them

Retention and deletion guarantees are out of scope for Phase 1 and are the responsibility of
the deploying party; this is noted here so it is not mistaken for a solved problem.

## LLM Boundary

Model-generated findings are untrusted advisory text. `lint_finding()` is the single safety
gate: it is enforced as a pipeline stage, not at object construction, so a malformed model
finding is rejected and quarantined rather than crashing the pipeline. Use
`quarantine_findings()` for batches of untrusted findings.

The gate enforces that:

- verdict language is scanned across ALL text fields (title, message, data gap, follow-up
  question, reference), with word-boundary matching so negated forms (e.g. "unsafe") are not
  falsely flagged and positive-sounding clearances (e.g. "good candidate", "within normal
  limits") are caught
- model-sourced `mechanics` findings are forbidden; deterministic rules own mechanics. Models
  may comment on data gaps, education, or follow-up questions only
- warning findings must include both a data gap and a follow-up question
- mechanics findings must reference a configured cap or citation

Every model-sourced finding must also carry model provenance, remain observational and
conditional, include data gaps when relevant, and avoid invented thresholds.

## Acquisition Advisor Boundary

The acquisition advisor is deterministic data-acquisition support. It toggles one missing
availability flag at a time, reruns the deterministic engine, and reports which
absence-of-data findings would clear, which suppressed checks would become assessable, and
which data-gap entries would close.

This is not treatment advice. "Would clear" means the engine would no longer flag the
absence of that data; it does not mean a movement, patient, or plan is safe or acceptable.
The advisor predicts nothing about what newly acquired data would show.

## Printing And Manufacturing Boundary

Print export settings, readiness checks, and generated packages are informational outputs from
the supplied plan data. Package manifests bind the output to plan/frame/artifact hashes and
label whether geometry came from segmented mesh bounds or schematic proxies. They do not make
a plan safe, suitable, or guaranteed to fit. Physical workflows depend on confirmed scale,
validated model materials, appropriate thermoforming sheets, post-processing controls,
cleaning procedures, and applicable regulatory compliance.

The app may list planned model artifact filenames and blockers. It must not claim that hobby
printer materials, unvalidated resins, or ordinary plastics are appropriate for intraoral use.

## Regulatory Note

This document is not legal advice. Anyone using or modifying this project is responsible for
their own use, privacy, materials, manufacturing process, and regulatory obligations.
