# Safety Boundary

OpenSource Ortho is a research and development safety playground for clear-aligner planning workflows. It can represent staged geometry and produce manufacturing-oriented exports, with STL-only surface review and reviewed CBCT/DICOM-derived root/bone-aware review when trusted anatomy is supplied. The current project is not distributed as medical device software, is not complete treatment-planning software, and is not intended to provide diagnosis, treatment approval, autonomous decision-making, or clearance for physical use.

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
- a generated package or appliance is safe, validated, or ready for intraoral use
- the software produces a complete treatment plan
- a patient is a good candidate for aligners
- roots, bone, periodontal structures, pathology, or airway status are acceptable when those data or reviewed derived anatomy are unavailable
- a movement threshold is authoritative unless it is either user-configured or cited

## Geometry, Not Biomechanics

The current STL path models crown-surface geometry only. It does not model force
levels, anchorage, attachment or IPR mechanics, tooth-movement feasibility, or
root-resorption risk. A proposed movement that fits within configured caps is a
geometric statement, not a biomechanical one. Visualization pivots (crown
centroid) are explicit display assumptions and never imply knowledge of root or
bone position.

CBCT/DICOM support is the higher-fidelity path to root/bone-aware review. Until
a CBCT record is locally ingested, registered to the STL, segmented or imported
as reviewed anatomy, and accepted by the relevant feature gate, root/bone-aware
checks must remain unavailable or explicitly marked as unassessed. CBCT presence
alone does not mean the volume was interpreted or that a plan is suitable.

The bundled `canonical-orthocad-001` root/bone fixture is an engineering fixture
used to exercise this gate sequence in the UI and tests. It uses redacted CBCT
metadata and safe derived anterior landmarks; it is not a clinical CBCT
segmentation, diagnosis, clearance, treatment approval, or evidence that raw
DICOM can be committed.

Per-tooth local frames (`ToothLocalFrame`) derived from crown-surface PCA are approximate
metadata only: their axes are ordered by geometric variance, not anatomy, and they do not
represent mesiodistal/buccolingual/long axes or root direction. PCA frames do not authorize
rotation rendering. Rotation is renderable only when the engine receives a non-approximate,
trusted anatomical frame or a global frame with resolved anatomical axes.

## Privacy Posture

Intraoral STL scans and CBCT/DICOM volumes are patient-derived data. The toolkit:

- never stores mesh bytes in serialized plans; only redacted asset metadata is kept
- strips directory structure and rejects absolute paths and parent-directory traversal,
  because export paths can embed patient names or DOB
- treats scan units as unverified until the user confirms them
- treats DICOM metadata as PHI-bearing; the canonical CBCT source files are kept
  local/ignored because identifier tags are present, while tracked fixtures carry
  only redacted structural metadata or safe derived landmarks

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

## Plan Generation Boundary

The "Generate Plan" action (`orthoplan/generation.py` + `orthoplan/planning/generate.py`)
is **deterministic** and produces a *proposal*, never an approval. It resolves a target from
whatever exists, in priority order:

1. **Authored** - existing per-tooth movement is re-staged into cap-sized increments.
2. **Landmark-derived** - when per-tooth crown **landmarks** (operator-identified crown
   centers, read from the visible scan) are supplied, the target is the real deviation of
   each tooth from the fitted arch, plus a deterministic arch-length/space analysis that
   budgets **IPR**, adds **attachments** on moved teeth, and attaches approximate per-tooth
   collision bounds. Landmarks carry an `approximate` flag; the space analysis uses a
   population crown-width table (a labeled heuristic with a data gap, not this patient's
   measured crowns). This is geometric processing of operator-identified visible positions -
   it infers no roots/bone and is not an approval.
3. **Geometry-derived** - when segmented per-tooth crowns exist, a straightening target is
   computed from their *visible* occlusal-plane positions by fitting a smooth arch curve
   (`planning/arch_form.py`). This is geometric processing of data already in the scan. It is
   explicitly a scan-axis heuristic: it does **not** infer roots, bone, or biological response,
   does not resolve mesiodistal/buccolingual axes, and is not a clinical alignment goal.
4. **Root/bone-aware review** - available only when registered CBCT/DICOM-derived
   anatomy is present, reviewed, and trusted. This path may add root axes, root proximity,
   and bone-boundary constraints, but those constraints must carry provenance and
   quality status and must fail closed when the CBCT record, registration, or
   segmentation is missing or uncertain. It is not a complete treatment plan.
5. **Educational-synthetic** - when only a raw scan is loaded, a clearly-labeled generic
   crowding template is used. The result is **not derived from the user's teeth**; it carries a
   prominent warning and `requires_acknowledgement`. This is a text warning, not a functional
   freeze - the engine still produces a visible educational preview.

The orchestration layer runs the generator, validates with the deterministic engine, and runs
a correctness review. Its verdict is **`CONSISTENT` / `ISSUES` / `NOT_APPLICABLE`** - a
statement that staging is internally consistent with the configured caps and fixed-tooth
controls, **never** that a plan is safe, approved, clinically appropriate, or complete. The
optional model review step is opt-in, gated on the same egress consent as the chat layer, and
its output passes the `lint_finding()` gate above (no `mechanics` findings, no verdict
language). With no connector, generation runs fully offline.

## Printing And Manufacturing Boundary

Print export settings, readiness checks, and generated packages are informational outputs from
the supplied plan data. Package manifests bind the output to plan/frame/artifact hashes and
label whether geometry came from segmented mesh bounds or schematic proxies. They do not make
a plan safe, suitable, or guaranteed to fit. Physical workflows depend on confirmed scale,
validated model materials, appropriate thermoforming sheets, post-processing controls,
cleaning procedures, and applicable regulatory compliance.

As CBCT/DICOM support is added, manifests should also label the review tier:
STL-only surface review, enhanced-records review, or root/bone-aware review. The
manufacturing output must preserve unresolved data gaps and registration /
segmentation quality rather than hiding them behind a printable file.

The app may list planned model artifact filenames and blockers. It must not claim that hobby
printer materials, unvalidated resins, or ordinary plastics are appropriate for intraoral use.

## Regulatory Note

This document is not legal advice. Anyone using, modifying, manufacturing from,
or physically applying outputs from this project is responsible for their own
use, risk, privacy, materials, manufacturing process, professional supervision,
and regulatory obligations. The software and generated outputs are provided
without warranty or liability for diagnosis, treatment, manufacturing, fit,
materials, injury, regulatory compliance, or any other use.
