# Development TODO

Updated: November 11, 2026. This backlog belongs to private development in
`john-lawniczak/OpenSourceOrtho-dev`. Follow
[the private development and release workflow](docs/PRIVATE_DEVELOPMENT.md).
Keep personal scans, CBCT pixels, and unpublished annotations out of public
release trees unless publication is explicitly authorized.

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

## Priority 1: establish a reviewed USER_ONE benchmark

- [ ] Select a small subset of teeth from the week 1 and week 7 endpoint scans.
- [ ] Obtain independently reviewed tooth boundaries and endpoint identities in
  machine-readable files bound to the exact source hashes.
- [ ] Record reviewer provenance, confirmed units, reference-region justification,
  and reference poses where available. Do not treat automatic fits as ground truth.
- [ ] Add repeat acquisitions with no intended movement when available; keep
  synthetic resampling tests separately identified.
- [ ] Measure boundary IoU/precision/recall, identity errors, translation and rotation
  errors, false motion, missing-fit coverage, and correction effort.
- [ ] Keep real accuracy explicitly unknown wherever independent truth is absent.

The existing synthetic stress benchmark produced false motion in **2 of 6**
independently resampled no-motion cases at thresholds of **0.05 synthetic-mm or
1 degree**. This demonstrates sensitivity to sampling; it is not a patient error
rate. See [the complete report](docs/benchmarks/motion-stress-2026-11-11.json).

## Priority 2: improve automatic segmentation against that benchmark

- [ ] Integrate a compatible trained dental model with documented provenance and
  licensing; an executable ONNX adapter alone does not establish model quality.
- [ ] Compare hybrid, surface-graph, and trained-model candidates against the same
  independently labeled cases, including held-out evaluation cases.
- [ ] Test gum leakage, touching teeth, missing teeth, scan defects, and FDI identity.
- [ ] Measure manual correction time as well as boundary accuracy before choosing
  a new default backend.

Segmentation is an upstream bottleneck: incorrect regions affect correspondence,
translation, rotation, and contact results. See
[the model contract and evaluation path](docs/segmentation-learned-backend.md).

## Priority 3: establish defensible registration and scale

- [ ] Verify and record USER_ONE's source scale before interpreting distances as mm.
- [ ] Compare whole-arch alignment with independently justified reference regions.
- [ ] Quantify how registration choice changes per-tooth movement estimates.
- [ ] Extend sensitivity checks across initialization, sampling, partial coverage,
  and independently repeated scans.
- [ ] Calibrate uncertainty against reviewed errors rather than equating low
  surface residuals or cycle consistency with correct tooth identity.

## Priority 4: improve simulation without overstating observations

- [ ] Compare timing assumptions and show how much intermediate poses depend on them.
- [ ] Add intermediate observed scans when available and evaluate estimates against
  those visits without using them to fit the same evaluation result.
- [ ] Extend contact checks along the motion path, including closed-mesh containment.
- [ ] Continue distinguishing held regions from evidence of no movement.
- [ ] Preserve the distinction between recorded endpoints, fitted endpoints, and
  simulated weeks in display, saved cases, and exports.

Two endpoints do not reveal the actual weekly path. Weeks 2–6 remain estimates
unless additional observations establish their positions. See
[simulation assumptions](docs/SIMULATION_ASSUMPTIONS.md).

## Priority 5: strengthen CBCT, root/bone, and bite tooling

- [ ] Review and correct CBCT masks against actual anatomy; intensity connectivity
  is not tooth, root, or bone identity.
- [ ] Validate STL-to-CBCT landmarks and registration using independent review.
- [ ] Review root-axis direction and geometry before downstream use.
- [ ] Improve beyond translation-only root-centerline proximity toward reviewed
  surface geometry and explicitly defined rotations.
- [ ] Establish a reviewed opposing-arch relationship before interpreting bite or
  inter-arch contact. The combined history view is only a display arrangement.

See [local CBCT review](docs/LOCAL_CBCT_REVIEW.md).

## Additional engineering follow-ups

- [ ] Expand target-generation evaluation beyond arch-form heuristics while
  keeping authored goals and geometric proposals distinguishable.
- [ ] Evaluate coupled staging and broader manual controls using known geometry.
- [ ] Strengthen case storage, migration, recovery, and collaboration workflows.
- [ ] Connect tooth-map and glossary references to relevant correction tasks.
- [ ] Evaluate shell/export geometry and manufacturing performance separately;
  software checks do not establish physical fit or authorize use.
- [ ] Resolve the GitHub account billing/spending-limit block and rerun hosted CI.
  Local test results do not substitute for a completed hosted run.

## Next milestone

Build the small independently reviewed USER_ONE benchmark first, then compare
segmentation candidates against it. Use measured errors and correction effort to
prioritize the next implementation phase. Do not raise accuracy ratings solely
because more features or synthetic tests have been added.

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
