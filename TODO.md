# Development TODO

Updated: November 11, 2026. This backlog belongs to private development in
`john-lawniczak/OpenSourceOrtho-dev`. Follow
[the private development and release workflow](docs/PRIVATE_DEVELOPMENT.md).
Keep personal scans, CBCT pixels, and unpublished annotations out of public
release trees unless publication is explicitly authorized.

OpenSource Ortho is a clear-aligner planning safety playground and research
toolkit. The roadmap deepens measurement, exploratory simulation, and review;
completing it does not establish clinical equivalence or authorize physical use.

## Current assessment

Overall: **7.00/10.00 as a research toolkit**. Visualization, correction workflows,
and traceability are the strongest areas. Demonstrating the accuracy of
automatically derived tooth movement remains the central gap.

These are engineering judgments about workflow maturity, not measured anatomical
accuracy. Two decimal places are a reporting convention, not measurement precision.
Recent shared-view and zoom improvements improve inspection; they do not validate
tooth boundaries, matches, or motion.

| Tool / area | Rating / 10.00 | Main remaining gap |
|---|---:|---|
| Scan import and inspection | 7.75 | Difficult scans still require cleanup. |
| Units and coordinate handling | 7.00 | USER_ONE's motion scale remains unverified. |
| 3D viewing and navigation | 8.00 | Continue testing shared-camera inspection across arches, weeks, and screen sizes. |
| Automatic surface segmentation | 6.00 | Draft boundaries can include gum or divide teeth incorrectly. |
| Learned-model integration | 6.00 | Adapter is tested; no trained dental model is installed and anatomically benchmarked. |
| Boundary and numbering corrections | 7.25 | Real-case correction burden is not measured. |
| Cross-visit registration | 7.00 | Whole-arch fitting can absorb real movement; stable reference selection needs justification. |
| Tooth correspondence between visits | 6.50 | Automatic tooth identity accuracy remains unmeasured. |
| Weekly movement simulation | 6.75 | Intermediate positions and timing remain assumptions. |
| Geometric target generation | 6.25 | Arch-form heuristics provide limited target reasoning. |
| Staging and movement controls | 7.25 | Coupled movement modeling remains limited. |
| Manual tooth editing | 7.25 | Guided movement controls remain limited. |
| Contact and proximity checks | 6.25 | Closed-mesh containment and contact throughout motion remain gaps. |
| Opposing-arch / bite review | 6.25 | Shared display placement does not establish a measured bite relationship. |
| CBCT, root, and bone workflow | 6.00 | Anatomical identification and correction remain substantially manual. |
| Two-visit cases, saving, and recovery | 7.25 | Storage and collaboration remain basic. |
| Accuracy benchmarking | 7.25 | Independent real-data ground truth is insufficient. |
| Local assistant and fit explanations | 7.00 | The helper explains metadata; it cannot independently inspect anatomy or validate matches. |
| Shell generation and export checks | 6.75 | Physical fit and manufacturing performance remain unestablished. |
| Tooth map, glossary, and guidance | 7.50 | References could connect more directly to case-specific correction tasks. |

## Quality gaps this roadmap addresses

The comparison with Invisalign highlights more than interface differences:

| Gap | Required improvement | Phases |
|---|---|---|
| Demonstrated measurement quality | Independent tooth labels, identities, poses, repeat scans, and held-out evaluation | 1–3 |
| Anatomical depth | Reviewed crown/root/bone geometry and independently checked registration | 2, 5 |
| Longitudinal tracking | Additional observed visits compared with estimates and authored stages | 4 |
| Editing and planning depth | Coupled tooth edits, arch-form controls, attachment/cut geometry, and interproximal spacing representation | 6 |
| Motion and material behavior | Path contact checks and explicit model assumptions; separately validated mechanical experiments | 6–7 |
| Review and operational reliability | Versioned cases, provenance, correction history, recovery, and review handoff | 1, 4, 8 |
| Export and physical performance | Reproducible geometry checks plus separate material/manufacturing evidence | 7–8 |

Official product descriptions document [ClinCheck editing and CBCT features](https://www.invisalign.com/provider/align-digital-platform/clincheck)
and [Align's progress assessment and integrated material/staging platform](https://www.invisalign.com/provider/align-digital-platform).
These identify comparison areas, not an independently measured accuracy advantage
or a specification to reproduce proprietary implementations.

## Execution order and completion rules

Use this order to address upstream errors before adding downstream complexity.
Extend existing modules and workflows; do not rebuild implemented features.

| Phase | Deliverable | Dependencies |
|---|---|---|
| 1 | Reproducible evidence and case contracts | Existing benchmark and case tools |
| 2 | Measured segmentation and correction improvements | Phase 1 evaluation contracts |
| 3 | Reliable reference frames and endpoint correspondence | Phases 1–2; reviewed masks can substitute for automatic masks |
| 4 | General multi-visit observation and estimate tracking | Phases 1 and 3 |
| 5 | Reviewed root/bone geometry and opposing-arch registration | Phases 1 and 3; can proceed alongside Phase 4 |
| 6 | Coupled editing and motion-path geometry checks | Phases 3–5 for features consuming those inputs |
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

## Phase 1 — establish evidence and provenance foundations

**Purpose:** make later improvements measurable and reproducible.

- [ ] Extend existing case/benchmark contracts to consistently bind source hashes,
  visit/arch identity, units, coordinate transforms, model/config versions, and
  reviewer decisions. Invalidate dependent results when these inputs change.
- [ ] Add a review-package workflow for a small USER_ONE week 1/week 7 tooth subset:
  export masks and candidate identities, import independent corrections, and
  record review provenance without treating automatic fits as ground truth.
- [ ] Verify USER_ONE scale; record unknown units until supporting evidence exists.
- [ ] Separate development, held-out, and repeat-scan cohorts. Split by subject for
  multi-subject data; label any USER_ONE-only evaluation as case-specific.
- [ ] Extend benchmark reports with boundary IoU/precision/recall, gum leakage,
  identity errors, translation/rotation errors, false motion, coverage, correction
  time, runtime, and peak memory. Declare denominators and unavailable metrics.
- [ ] Obtain independently reviewed labels, endpoint correspondences/reference
  poses, and repeat acquisitions with no intended movement. Keep synthetic
  resampling and actual repeat acquisitions in separate result categories.
- [ ] Prespecify task-specific evaluation thresholds and regression budgets before
  assessing held-out results; do not invent universal clinical tolerances.

**Code completion:** fixtures reject mismatched hashes, frames, units, or stale
reviews; identical inputs reproduce reports; missing truth reports unknown.
**Evidence completion:** the reviewed subset has traceable annotations and a
baseline report; unavailable repeat scans and poses remain explicit gaps.

Existing synthetic stress results show false motion in **2 of 6** independently
resampled no-motion cases at **0.05 synthetic-mm or 1 degree**. This is a sampling
sensitivity result, not a patient error rate. Preserve
[the baseline report](docs/benchmarks/motion-stress-2026-11-11.json).

## Phase 2 — improve segmentation and reduce correction effort

- [ ] Integrate a compatible trained dental model with documented weights, license,
  provenance, and input/output contract through the existing plug-in interface.
  The tested ONNX adapter is infrastructure, not an installed dental model.
- [ ] Compare hybrid, surface-graph, and learned candidates on the same reviewed
  corpus, keeping evaluation cases out of tuning.
- [ ] Strengthen gum exclusion, touching/missing-tooth handling, disconnected-region
  detection, FDI proposals, and defect handling using measured failure cases.
- [ ] Improve existing brush/split/merge/numbering correction where measured effort
  is highest; retain undo and source-bound edits after save/reload.
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
  axes, pivots, arch-form edits, undo/redo, and deterministic regeneration.
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
- [ ] Test storage migrations, interrupted saves, corruption detection, backup/restore,
  concurrent edits, and large-case limits before adding shared case collaboration.
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

Start with Phase 1's review-package round trip, stale-result detection, and benchmark
report extensions using synthetic fixtures and existing USER_ONE candidates.
In parallel with that coding, obtain independent annotations and confirm scale.
Then run Phase 2 candidate comparisons and Phase 3 registration experiments against
the same frozen evidence. Do not raise accuracy ratings solely because features
or synthetic tests have been added.

Related records: [implementation phases](docs/TOOL_IMPROVEMENT_PHASES.md),
[prior research workflow scorecard](docs/TOOL_SCORECARD.md),
[two-visit workflow](docs/TWO_VISIT_WORKFLOW.md), and
[boundary corrections](docs/REGION_CORRECTIONS.md).

## Completed follow-up: endpoint assignment reliability

- [x] Exclude infeasible candidates before one-to-one assignment; provide explicit
  unmatched choices so invalid edges cannot displace valid matches.
- [x] Record competing assignment costs and flag nearly tied identities as uncertain
  without disabling best-effort motion previews.
- [x] Initialize match review from the actual independent candidate rather than
  assuming equal FDI numbers across independently segmented visits.
- [x] Refresh USER_ONE artifacts and expose ambiguity in selected-tooth details.

These changes improve the matcher and its inspectability. They do not establish
anatomical identity accuracy or replace the independently reviewed benchmark.
