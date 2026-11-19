# Development TODO

Updated: November 15, 2026. This backlog belongs to private development in
`john-lawniczak/OpenSourceOrtho-dev`. Follow
[the private development and release workflow](docs/PRIVATE_DEVELOPMENT.md).
Keep personal scans, CBCT pixels, and unpublished annotations out of public
release trees unless publication is explicitly authorized.

OpenSource Ortho is a clear-aligner planning safety playground and research
toolkit. The roadmap deepens measurement, exploratory simulation, and review;
completing it does not establish clinical equivalence or authorize physical use.

This file lists remaining work only. Implemented workflows and the November 15
week-18 display changes are documented in
[local research workflows](docs/LOCAL_RESEARCH_WORKFLOWS.md) and
[scan history](docs/SCAN_HISTORY.md). Commit history retains prior work records.

## Next USER_ONE work

- [ ] Build a reproducible H4/H6 capture-consistency report with exact source/label
  hashes, configuration, per-tooth apparent movement, residuals, coverage, and
  explicit unmatched regions. Repeat with different registration choices and
  surface samples; keep unknown scale in scan units. No H4/H6 report has been run.
- [ ] Review the same small intact tooth subset in original H4 and H6, save each
  painting and notes separately, and map the suspected FDI 32 chip surface and
  protruding H6 material. The
  contributor confirmed on November 15 that the physical model was unchanged
  between H4/H6 and the chip predated both. See the [review steps](docs/LOCAL_RESEARCH_WORKFLOWS.md#prepare-an-h4h6-repeatability-check).
- [ ] Review the prepared edited-H6 painting, especially suspected model chip
  FDI 32, partial FDI 41 coverage and protruding material; refine cleanup and save.
  Keep this six-trim variant distinct from original H6 in repeatability reports.
- [ ] Inspect the trimmed H4 margin around draft FDI 43, where cleanup removed
  28 labeled faces. Display selection does not establish boundary accuracy.
- [ ] Add source-bound week-18 endpoint fitting using the selected captures and
  available corrections; keep weak/unmatched regions visible and intermediate
  poses estimated. The approximate bite display supplies no motion/bite truth.
- [ ] Add surface-area-weighted agreement and boundary-distance scoring to the
  contributor agreement report, with unknown surfaces distinct from reviewed gum.

## Primary input — each user's own model

Contributor clarified on November 12, 2026: the intended primary input is each
individual user's own model/scan, including personally made physical models.
Professional intraoral scans are optional comparison evidence for development,
not a prerequisite for using exploratory tools. Preserve the user's observed
geometry; do not replace it with a generic ideal arch. Measure errors from
impression/model making, scanning, segmentation and registration separately.

- [ ] Evaluate the local-model workflow against a closely timed professional
  capture when available; record units, dates, bite alignment, model/impression
  identities and repeat captures. Repeated scans of one cast measure scanner
  repeatability; independent casts also test model-making variability.
- [ ] Assess complementary intact donor regions before attempting any composite.
  Require compatible observation time, arch, scale and registration; retain
  source hashes, per-region provenance, defect masks and the original files.
  Never count inferred hole filling as observed anatomy or use a later-week
  surface as a verified week-18 replacement. Keep composites in the same
  subject/source family for benchmark splitting to avoid evaluation leakage.

## Current assessment

Visualization, correction workflows, and traceability are implemented. Measured
accuracy of automatically derived tooth boundaries, identities, and motion is
still the central gap. Prior subjective /10 ratings are retired as progress
criteria; feature availability and evidence quality must be reported separately.

| Area | Current evidence/status | Next measured result |
|---|---|---|
| Source intake and units | Source hashes recorded; USER_ONE scale unverified | Verified scale provenance and rejected stale-source cases |
| Boundary correction | USER_ONE upper/lower painting saved; 28 labels each have one connected region | Independent boundary review, gum leakage, per-tooth IoU, correction time |
| Automatic segmentation | Local drafts and model adapter exist; trained dental model evaluation pending | Held-out boundary/identity/coverage comparison and correction effort |
| Registration and correspondence | Fit and ambiguity diagnostics exist | Reference-frame sensitivity, identity errors, repeat-scan false motion |
| Motion preview | Estimated intermediate poses exist; real pose accuracy unknown | Translation/rotation errors where independent reference poses exist |
| Multi-visit records | Multiple captures per endpoint, active selection, and portable saves exist | Ordered multi-visit graph and tracking |
| Manual editing | Movement controls, undo/redo, and bound session recovery exist | Multi-tooth edits, explicit axes/pivots, named alternative comparison |
| Recovery and review | USER_ONE per-tooth reviews, source-bound refits, and invalidation exist | Independent review-package round trips and generalized uploaded-case reviews |
| Anatomy, mechanics, and exports | Exploratory components; independent evidence incomplete | Input-specific geometry tests and separate physical experiments |

Every result must state corpus/version, sample count, denominator, units, coverage,
and unavailable metrics. Keep development annotations separate from held-out
independent reference labels. One contributor's corrections improve a draft but
do not establish anatomical ground truth or a population accuracy estimate.

## Execution order and completion rules

Phase numbers identify workstreams, not a requirement to finish every earlier
phase first. Keep measurement contracts first, then develop visit intake and basic
editing alongside segmentation/registration evaluation. Extend existing modules;
do not rebuild implemented features.

| Phase | Deliverable | Dependencies |
|---|---|---|
| 1 | Reproducible evidence and case contracts | Existing benchmark and case tools |
| 2 | Measured segmentation and correction improvements | Phase 1 evaluation contracts |
| 3 | Reliable reference frames and endpoint correspondence | Phases 1–2; reviewed masks can substitute for automatic masks |
| 4 | Ordered multi-visit intake and fitted tracking | Extend existing multi-capture saves; comparisons need Phase 3 evidence |
| 5 | Reviewed root/bone geometry and opposing-arch registration | Phases 1 and 3; can proceed alongside Phase 4 |
| 6 | Early basic editing; later coupled/path geometry checks | Basic edits need explicit frames and revisions; anatomy-dependent checks need Phases 3–5 |
| 7 | Evaluated simulation models and export geometry | Phase 6 |
| 8 | Durable review, recovery, and handoff | Builds incrementally from Phase 1; integrates Phases 4–7 |

For every phase, commit coherent changes with behavior, validation, and remaining
limitations in the commit message. Record reproducible commands, fixture/model
versions, and results. Run relevant tests and the maintainability check; keep
rendering, geometry, evaluation, and provider adapters separate.

A phase has two distinct milestones: **code verified** and **evidence obtained**.
Synthetic fixtures can satisfy software contracts while real-data evaluation is
pending. Do not check off an evidence task or promote a model based on synthetic
tests alone. Missing reviewed data must not disable clearly labeled best-effort
previews; show uncertainty, held regions, and missing inputs explicitly.

## Immediate next steps — USER_ONE segmentation benchmark

Both baseline arches are painted and versioned. Contributor-approved cleanup
cleared 260 upper and 38 lower detached face labels to context without changing
the source geometry. All 28 tooth labels have one connected region. This verifies
connectivity, not anatomical accuracy. Current checkpoints:
[upper](datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/annotations/initial-upper-fragment-cleanup-2026-11-12T190542Z.json)
and [lower](datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/annotations/initial-lower-fragment-cleanup-2026-11-12T195642Z.json).

- [ ] **Finish boundary review.** Inspect chewing surfaces, inner surfaces,
  interproximal contacts, gum margins and FDI identities on both arches. Obtain
  a second knowledgeable review; record reviewer, scope, disagreements and
  uncertain regions separately from the contributor's painting confirmation.
- [ ] **Freeze benchmark v1.** Bind immutable label maps to original scan hashes,
  tooth inventory, annotation/review versions, scale provenance and unresolved
  uncertainty. Preserve previous checkpoints. Do not promote these development
  labels to independently reviewed truth solely because connectivity passes.
- [ ] **Score automatic segmentation against the reference.** Compare the original
  automatic proposals and candidate algorithms on the same source faces. Report
  tooth identification, per-tooth IoU/precision/recall, boundary distances, gum
  leakage and coverage. Declare units and unavailable correction-time measures;
  do not infer an anatomical accuracy percentage from connectivity.
- [ ] **Independently evaluate the saved week 1–7 refits.** Review endpoint
  identities/boundaries and compare against independent evidence. The local
  corrected-label refits have already run; lower residuals and fewer weak fits
  do not establish motion accuracy. Keep weeks 2–6 estimated and separate from
  authored treatment-plan data.
- [ ] **Expand to other independently reviewed cases.** Obtain appropriately
  licensed/consented scans from different people, split development and held-out
  evaluation by person, and measure generalization and correction effort. Keep
  USER_ONE results case-specific; multiple visits of one person are not an
  independent population test set.

## Phase 1 — establish evidence and provenance foundations

**Purpose:** make later improvements measurable and reproducible.

- [ ] Extend existing case/benchmark contracts to consistently bind source hashes,
  visit/arch identity, units, coordinate transforms, model/config versions, and
  reviewer decisions. Invalidate dependent results when these inputs change.
- [ ] Add a review-package workflow for a small USER_ONE week 1/week 7 tooth subset:
  export masks and candidate identities, import independent corrections, and
  record review provenance without treating automatic fits as ground truth.
- [ ] Complete review metadata for the saved contributor baseline annotations:
  record which teeth/surfaces were inspected, uncertainty, annotator role, and
  time where available; do not invent missing historical correction times.
  Keep contributor labels distinct from independently reviewed reference labels.
- [ ] Extend existing USER_ONE per-tooth reviews to uploaded cases and independent
  reviewers; add explicit unknown-boundary/model-defect masks and surface-level
  review scope. Preserve originals and distinguish model damage from anatomy.
- [ ] Bind the contributor-reported JMStudio millimetre export setting to exact
  USER_ONE files and add dimensional calibration evidence; retain unknown scale
  for files without unit confirmation.
- [ ] Separate development, held-out, and repeat-scan cohorts. Split by subject for
  multi-subject data; label any USER_ONE-only evaluation as case-specific.
- [ ] Connect the existing agreement and motion scorers to independently reviewed
  cases; add gum leakage on reviewed context, measured correction time, segmentation
  runtime, and peak memory. Declare denominators and unavailable metrics.
- [ ] Obtain independently reviewed labels, endpoint correspondences/reference
  poses, and repeat acquisitions with no intended movement. Keep synthetic
  resampling and actual repeat acquisitions in separate result categories.
- [ ] Prespecify task-specific evaluation thresholds and regression budgets before
  assessing held-out results; do not invent universal clinical tolerances.

**Code completion:** fixtures reject mismatched hashes, frames, units, or stale
reviews; identical inputs reproduce reports; missing truth reports unknown.
**Evidence completion:** the reviewed subset has traceable annotations and a
baseline report; unverified repeat conditions and missing reference poses remain
explicit gaps.

Existing synthetic stress results show false motion in **2 of 6** independently
resampled no-motion cases at **0.05 synthetic-mm or 1 degree**. This is a sampling
sensitivity result, not a patient error rate. Preserve
[the baseline report](docs/benchmarks/motion-stress-2026-11-11.json).

## Phase 2 — improve segmentation and reduce correction effort

- [x] **The code-only path is fully open and improvable right now.** No public
  dataset is license-clear enough to train and ship a crown-segmentation model
  (see `docs/segmentation-learned-backend.md`), so keep improving the
  dependency-free heuristic/hybrid/surface-graph segmenter as the near-term
  route - it needs no external dataset and is not blocked by this.
  **Started 2026-11-19:** `SurfaceGraphSegmenter` had zero test coverage and
  was invisible to the synthetic measurement lab (fixture mismatch, see
  `docs/segmentation-learned-backend.md`). Added real-scan test coverage
  (`tests/test_surface_graph_segmenter.py`) and measured it: it already beats
  the hybrid's compactness on 3 of 4 metrics on the bundled scans. Fixed its
  confidence value (was a flat ~0.5 placeholder; now reflects per-region
  compactness, capped by the upstream draft's own confidence). Investigated
  the one regressed metric (upper-arch min compactness): it is a pre-existing
  weak spot SHARED by the hybrid (same worst tooth, 27, in both) - inherited
  from the hybrid draft, not something to patch narrowly here; left open,
  documented in `docs/segmentation-learned-backend.md`. Remaining in this
  item: decide whether to promote `SurfaceGraphSegmenter` to the active
  backend (`load_local_segmenter()` still returns the hybrid).
- [ ] Integrate a compatible trained dental model with documented weights, license,
  provenance, and input/output contract through the existing plug-in interface.
  The tested ONNX adapter is infrastructure, not an installed dental model.
- [ ] Compare hybrid, surface-graph, and learned candidates on the same reviewed
  corpus, keeping evaluation cases out of tuning.
- [ ] Strengthen gum exclusion, touching/missing-tooth handling, disconnected-region
  detection, FDI proposals, and defect handling using measured failure cases.
- [ ] Improve existing brush/split/merge/numbering correction where measured effort
  is highest; retain undo and source-bound edits after save/reload.
- [ ] Add isolation/context toggles and saved viewpoints to the existing tooth
  selection/highlight and visible-surface brush workflow. Measure correction effort
  before prototyping contour-to-surface labeling; screen-space lines must not
  silently label hidden or opposite surfaces.
- [ ] Profile inference and correction costs before adding caching, workers, or
  mesh reduction; measure any accuracy loss from reduced geometry.

**Code completion:** regressions cover touching/missing teeth, scan defects, invalid
model output, and edit round trips. **Evidence completion:** publish boundary,
identity, coverage, and correction-effort comparisons before changing the default
backend. See [the model evaluation contract](docs/segmentation-learned-backend.md).

## Phase 3 — strengthen registration and endpoint correspondence

- [ ] Compare whole-arch fitting with independently justified stable reference
  regions; expose how frame choice changes estimated per-tooth movement.
- [ ] Extend distance/normal, bidirectional, initialization, sampling, and partial
  coverage checks; keep fit residual, identity ambiguity, and reference-frame
  uncertainty as separate evidence.
- [ ] Evaluate assignment alternatives against reviewed identities, including missing
  teeth and ambiguous matches. Preserve explicit unmatched and manual overrides.
- [ ] Measure false motion on repeat acquisitions and calibrate uncertainty against
  reviewed errors; do not interpret low residuals as correct identity probability.
- [ ] Preserve original scans and compose explicit transforms instead of repeatedly
  baking transforms into geometry or silently recentering each visit.

**Code completion:** known-transform fixtures recover the expected poses; rigid
scanner-frame changes do not create tooth movement; missing/ambiguous identities
remain explicit. **Evidence completion:** report registration-choice sensitivity,
identity errors, repeat-scan false motion, and pose errors where truth is available.

## Phase 4 — generalize to multi-visit progress tracking

- [ ] Extend the two-visit workflow to an ordered series of visits with arch, date,
  reported treatment week, units, and source provenance; handle missing arches.
  Begin this intake work alongside Phases 1–3; fitting evidence is not required
  to retain or inspect an original observation.
- [ ] Record whether repeat captures share a physical model and document model
  damage/repair history. Same-model repeats can test capture consistency but
  cannot establish undamaged anatomy or independent tooth-motion accuracy.
- [ ] Maintain tooth identities across visits with reviewed corrections and explicit
  missing/uncertain links; compare adjacent and baseline-to-visit fits for drift.
- [ ] Compare an observed visit with a user-selected authored stage in a justified
  common frame. Keep inferred history separate from authored planning data.
- [ ] Display per-tooth observed-versus-estimated differences, uncertainty, coverage,
  and missing results with source links and persistent camera/selection state.
- [ ] Evaluate intermediate estimates on held-out observed visits without fitting
  those same visits; show timing-assumption sensitivity in the meantime.
- [ ] Extend portable cases and local persistence to round-trip the visit graph,
  corrections, assumptions, and derived results with version migrations.

**Code completion:** tests cover out-of-order imports, missing arches/teeth,
corrected identities, stale-result regeneration, and save/reload. **Evidence
completion:** evaluate tracking on additional observations when available. Weeks
2–6 remain estimates until observed scans establish their positions; held regions
are not evidence of no movement. See [simulation assumptions](docs/SIMULATION_ASSUMPTIONS.md).

## Phase 5 — deepen CBCT anatomy and measured bite relationships

- [ ] Improve existing CBCT mask review/correction and candidate segmentation;
  intensity connectivity alone must not assign tooth/root/bone identity.
- [ ] Validate STL-to-CBCT landmark registration with independent checks and review
  root-axis direction, mask coverage, and geometry before downstream use.
- [ ] Replace translation-only root-centerline proxies where supported with reviewed
  surfaces transformed using the full rigid pose, including rotation and pivots.
- [ ] Capture/import a measured opposing-arch relationship with source bindings,
  units, transform checks, and review provenance.
- [ ] Propagate anatomical uncertainty and incomplete coverage into derived checks;
  do not infer bite registration from the shared-scene display arrangement.

**Code completion:** known transforms preserve crown/root relationships and patient
coordinates; tests cover rotations, nonidentity affines, out-of-field geometry,
reflection/scale rejection, and changed sources. **Evidence completion:** reviewed
anatomy, independently checked registration, and measured bite data are required
for their respective real-case claims. See [local CBCT review](docs/LOCAL_CBCT_REVIEW.md).

## Phase 6 — add coupled editing and motion-path geometry checks

- [ ] Extend existing manual controls with multi-tooth selection, explicit local/world
  axes, pivots, arch-form edits, and deterministic regeneration; preserve the
  implemented undo/redo and source-bound recovery.
  Start basic editing alongside Phases 1–4; do not wait for CBCT or mechanics.
- [ ] Save and compare alternative authored revisions without overwriting observed
  scans, boundary annotations, or inferred scan-history motion.
- [ ] Represent authored attachment/cut geometry and interproximal spacing requests
  as inspectable parameters; distinguish authored goals from generated proposals.
- [ ] Evaluate target generation beyond arch-form heuristics on known geometry;
  expose conflicting constraints and infeasible requests rather than hiding them.
- [ ] Add closed-mesh containment and adaptive motion-path contact checks, reporting
  numerical tolerance, sampling bounds, mesh validity, and unresolved intervals.
- [ ] Apply checks to coupled motion and reviewed opposing arches/root surfaces when
  available; keep incomplete or budget-exhausted checks explicitly indeterminate.

**Code completion:** fixtures cover containment without triangle intersection,
collisions between sampled endpoints, coupled rotations, edit rollback, and
infeasible constraints. Geometry features must not imply measured forces,
biological response, or an automatically appropriate treatment choice.

## Phase 7 — evaluate simulation models and export geometry

- [ ] Compare timing profiles and coupled staging assumptions against held-out
  observations; preserve original endpoints, fitted endpoints, and estimated frames.
- [ ] Define a mechanics plug-in contract for explicit material properties, contact,
  boundary conditions, solver convergence, and reproducible parameter studies.
  Keep experimental mechanics separate from the default geometric preview.
- [ ] Validate any mechanical solver first on analytical/controlled fixtures, then
  on independent physical measurements; obtain suitable material/force data before
  making performance claims. A solver interface alone is not validated mechanics.
- [ ] Strengthen shell/export checks for topology, thickness, inner/outer clearance,
  units, tolerances, and attachment/cut geometry; retain source/config provenance.
- [ ] Measure physical fit, material response, and manufacturing repeatability through
  separate expert-led experiments. Keep these evidence tasks open without results.

**Code completion:** reproducible simulations and exports have explicit assumptions,
convergence/failure states, and geometric regression reports. **Evidence completion:**
observed motion and physical experiments support only the tested conditions; rigid
interpolation or successful file export does not establish physical performance.

## Phase 8 — harden case review, recovery, and handoff

- [ ] Build on Phase 1 provenance with durable case revisions, review comments,
  result invalidation, audit history, and reproducible exports of reviewed versions.
- [ ] Add a complete portable profile backup/restore with original scans, painting,
  notes and settings; verify restoration into a fresh browser independently of USER_ONE.
- [ ] Extend profile recovery checks to interrupted writes, corrupted snapshots,
  later schema migrations and large-case limits. Local profile switching, legacy
  upload retention, failed saves and stale workspace revisions are covered.
- [ ] Add access controls and conflict handling if shared storage is introduced;
  retain private-data boundaries in exports and public release preparation.
- [ ] Connect guidance and glossary entries to correction tasks. Keep assistant
  findings source-linked and passed through `lint_finding()` before display/export.
- [ ] Add explicit handoff manifests for external review/manufacturing experiments;
  distinguish review status from authorization for treatment or physical use.
- [ ] Resolve the GitHub account billing/spending-limit block and rerun hosted CI.
  This account task can proceed now; local tests do not establish hosted success.

**Code completion:** recoverability and migration tests pass, reviewed revisions
can be reproduced, stale results cannot silently retain review status, and release
checks exclude unauthorized private assets. Record the actual hosted CI result.

## Immediate next coding increment

Deliver one complete research workflow:
**import multiple visits/captures → correct identities and crown boundaries →
inspect estimated motion → compare with observations → save and reopen**.

1. Start a small USER_ONE contributor annotation session using the current editor.
   Save source-bound corrections and record partial coverage/uncertainty; leave
   the whole-scan reviewed checkbox off until the whole scan has been checked.
2. Add independent review-package round trips and the H4/H6 report; extend the
   existing invalidation checks to imported reviews. Obtain scale evidence.
3. Extend current two-endpoint/multi-capture saves to an ordered visit graph.
   Keep private local access separate from public dataset allowlists.
4. Improve basic editing and annotation usability while comparing segmentation
   candidates and registration choices against the same frozen reviewed corpus.
5. Keep anatomy-dependent checks, mechanics, and manufacturing experiments later,
   with their own data requirements and evidence milestones.

**Next acceptance demonstration:** reopen an H4/H6 report with its exact source
and label versions; reproduce the measurements and distinguish registration/
sampling sensitivity from physical changes. Missing truth stays unknown and
must not disable exploratory previews.

## What a contributor can provide now

- Original scans and visit/arch labels, with acquisition dates distinguished from
  contribution dates; identify repeat scans of the same physical model.
- Scanner/export unit settings or a documented measurement on the scanned model;
  do not infer millimeters from tooth appearance alone.
- A few carefully labeled tooth surfaces from several views, including tooth/gum
  transitions and uncertain boundaries. Save the editor JSON, not just screenshots.
- Model-defect descriptions and marked locations, including chips, repairs, and
  trimming. Do not reconstruct missing tooth anatomy from a chipped model by guess.
- Tooth-number corrections where known; otherwise record uncertainty and confirm
  orientation/numbering before using labels for cross-visit correspondence.
- Independent review of selected annotations when available. Reserve reviewed
  evaluation cases from tuning and report contributor-only results as such.

Use [the current boundary-review workflow](docs/REGION_CORRECTIONS.md) to begin.
The editor supports painting, tooth selection/highlighting, and undo/redo.
USER_ONE per-tooth contributor reviews are available in Explore individual teeth;
independent review exchange, contour filling, and spatial uncertainty/defect
layers remain open.

Related records: [implementation phases](docs/TOOL_IMPROVEMENT_PHASES.md),
[prior research workflow scorecard](docs/TOOL_SCORECARD.md),
[two-visit workflow](docs/TWO_VISIT_WORKFLOW.md), and
[boundary corrections](docs/REGION_CORRECTIONS.md).
