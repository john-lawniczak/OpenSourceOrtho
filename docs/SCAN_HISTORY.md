# Endpoint-based weekly progress

The application should use and improve existing tooth-segmentation tools to
obtain usable endpoint matches and simulate the gaps between scans. Two visits
are enough to attempt a **best-effort research preview**. Intermediate scans are
not a prerequisite; the UI distinguishes inferred poses from observations.

## Repository review and resulting implementation

The repository already provided a local hybrid segmenter, a learned-model
plug-in contract, segmentation quality reports, and a hypothetical planning
viewer. It lacked a connection from two actual visits to per-tooth fitted
motion. The earlier scan-history implementation switched whole surfaces and
withheld intermediate frames. That behavior did not serve the product goal.

`orthoplan/longitudinal/` now owns endpoint fitting, separate from plan authoring
and rendering. `load_local_segmenter()` supplies tooth-region drafts; an installed
local learned backend can replace the geometric fallback without changing the
matching pipeline. Generation runs locally, with no hosted inference.

1. Verify both original STL hashes and apply the documented display rotations
   and bounding-box centering. Retain source coordinate scale.
2. Segment both visits with the active local segmenter. Record quality reports
   without treating the production-candidate gate as a preview gate.
3. Trim outliers while fitting the later whole arch to the earlier arch using
   rigid ICP. There is no scale fitting. The reference is a whole-arch best fit,
   not stable anatomical landmarks; global arch motion may be removed.
4. Compare independently segmented regions with one-to-one spatial/size
   assignment. Independent cuts can drift and misidentify neighboring regions.
   Transfer baseline crown masks onto the aligned target surface by nearest
   baseline surface location with distance, normal, and round-trip checks to stabilize region identity. Each target face
   receives at most one baseline region label. Independent label disagreements
   remain uncertainty signals.
5. Fit a rigid pose for each baseline region to its corresponding target region.
   The crown mask uses the upper 65% of each draft region's face-centroid heights;
   it is a rough geometric mask, not an established gingival margin. Fitting uses
   deterministic area-weighted surface samples and symmetric residual checks.
6. For reported week `w`, select a timing assumption (uniform uses `(w - 1) / 6`) and interpolate pivot translation and
   rotation by shortest-path quaternion SLERP. Each region stays rigid. Surface
   context outside the moving masks remains fixed; gaps and overlaps can appear.
7. Display original surfaces at weeks 1 and 7. At week 7 the user can toggle the
   fitted baseline endpoint to compare it with the recorded surface. All
   intermediate frames have a persistent **SIMULATED ESTIMATE** label.

No orthodontic target, crowding template, treatment plan, or week 18 scan enters
this fit. Source STL bytes remain unchanged. Artifact hashes bind the preview to
the exact public endpoint files and rotations. The contributor's confirmation of
input alignment/correspondence remains distinct from these new unreviewed fits.

## Quality evidence and current limits

The bundled fallback produces 14 draft regions per arch. The current fit moves
13 upper and 14 lower regions; one upper region lacks usable projected target
coverage and stays fixed. These counts describe algorithm outputs, not verified
tooth anatomy. FDI numbering and boundaries remain drafts, and the baseline
heuristic can include gingiva or parts of neighboring crowns.

The UI exposes each region's draft/uncertain/held status, estimated pivot shift,
rotation magnitude, and symmetric 90th-percentile surface residual. Independent
label disagreement or weak geometric fit flags an uncertain match; it does not
turn the entire preview off. Missing data, non-finite/degenerate fits, and gross
assignment failures must not become fabricated motion. Held regions are counted
explicitly and their zero motion does not mean the actual tooth was stationary.

Shift and residual values are **scan units**, since progress scale has not been
verified. Residuals measure fit, not clinical accuracy or probability of correct
identity. All offered interpolation profiles are timing assumptions: actual movement could
start, pause, reverse, or follow another path. Reported week labels also differ
from elapsed time between the recorded acquisition dates.

Further improvements should prioritize reviewed crown boundaries, stable
registration references, mesh-aware correspondence, and synthetic/annotated
motion benchmarks. Improving the segmenter or correspondence should improve the
preview without changing its observation/estimate distinction.

## Reproduce and verify

The browser consumes checked-in derived artifacts, so normal app startup needs
no SciPy/NumPy installation. For local artifact generation:

```bash
pip install -e ".[dev,motion-preview]"
python tools/build_sample_motion.py
python tools/build_dataset_catalog.py
python -m pytest tests/test_endpoint_motion.py tests/test_sample_motion_artifacts.py -q
npm test --prefix ui
python3 tools/check_maintainability.py --strict
```

The two `derived/progress-01-motion-*.json` artifacts contain the transforms,
source hashes, encoded face labels, fit evidence, segmentation reports, and
linted model-provenance advisories. They are derived only from the already
published endpoint scans and fall within the existing derived-preview scope.
Private contributions remain outside the HTTP asset allowlist.

Numerical tests recover known transforms, reject reflections/degenerate data,
retain identity motion, test reordered regions and uncertain fits, and verify
projection ownership. Browser tests verify distinct weekly poses, source/estimate
labels, selected-tooth continuity, camera preservation, the week 7 comparison,
mobile layout, failure recovery, and separation from authored planning.

## Additional workflows

Both arches are displayed in separate simultaneous viewports by default. They
share timeline commands, without implying a bite registration. Right-side zoom
controls and highlighted week buttons support close inspection.

See [accuracy scoring](MOTION_BENCHMARK.md), [region correction](REGION_CORRECTIONS.md),
[registration diagnostics](ENDPOINT_REGISTRATION.md), [two-visit cases](TWO_VISIT_WORKFLOW.md),
and [timing and proximity](SIMULATION_ASSUMPTIONS.md). Reviewed real truth and
no-motion repeat scans remain necessary for measured anatomical accuracy.

## Independent assignment ambiguity

Independent draft-region matching excludes infeasible distance edges before the
one-to-one optimization and provides explicit unmatched choices. This prevents a
far-away candidate from displacing a better valid match before being discarded.
The optimizer first maximizes feasible match count, then minimizes normalized
centroid/size cost. These are geometric proposals, not anatomical identities.

For each selected pair, the matcher also solves the assignment with that edge
removed. If an alternative preserves match count and increases total cost by at
most 0.05, the identity is marked ambiguous. This dimensionless heuristic is not
a probability or calibrated accuracy threshold. Candidate regions and the cost
difference appear in selected-tooth details; the preview remains available with
an uncertain status. Explicit corrected labels and match overrides remain
separate from this automatic evidence.

The match-review dropdown starts with the actual independent candidate, including
an unmatched state, instead of assuming that independently assigned FDI labels
must agree. The refreshed USER_ONE artifacts flag six upper-region assignments as
ambiguous; fitted translations and rotations are unchanged by this diagnostic.

## Painted USER_ONE workspace

The test case's **Explore individual teeth** opens the saved week 7 upper and
lower regions. Choose **Week 1** to inspect the baseline painting, or **Reload
saved painting** after saving another draft. Section 3 accepts either FDI or US
Universal numbers; the selected crown uses exactly that annotation's source
triangles. Missing regions are reported rather than approximated by a strip.

`POST /api/sample-teeth` resolves each arch independently: latest validated local
save, then the hash-checked private annotation index. The baseline can also use
its bundled draft. Week 7 does not silently substitute heuristic segmentation.
Private archives incorporate the contributor's saved drafts for reproducible DEV
use; they do not change source scans, publication consent, or review status.

Selection and camera navigation work without reviewing the draft. Millimetre
edits still require confirmed scan scale and explicit review of the selected
region's identity and boundary. Week 7 units remain unverified. Stages begin with
zero movement; these exploratory edits are separate from the existing scan-history
motion estimates, which are not refitted by loading a painting.

Both arches open face-on. Week 7's separately exported arches use a display-only
layout (upper crowns down, lower crowns up), with the identical transform applied
to their painted fragments. Their displayed separation is not bite registration.
Rotate, Pan, Focus selected tooth, and the view presets move only the camera.

`tools/record_workflow_demo.py` records the private painted workspace to the
case's `private/media/` folder. The local server serves its video, captions, and
poster through the three fixed `/workflow-*` routes; without those private assets,
the bundled public walkthrough remains the fallback. Public release filtering
excludes these private recordings and annotations.

## Observed week 18

The sample history now exposes reported weeks 1–18. The original week 18 upper
and lower pair loads on demand from its published visit manifest and source
metadata, with SHA-256 verification. Acquisition date remains unknown. Display
centering and scanner-axis assumptions are not cross-visit or bite registration.

Weeks 2–6 retain the existing week 1–7 fit. Weeks 8–17 explicitly show **Not fitted**;
week 18 is an observation and does not inherit earlier tooth labels, motion or
proximity values. Week 18 painting links open that exact arch and visit with
separate saves. After painting, a new endpoint fit can attempt a best-effort
week 1–18 research preview, retaining uncertainty for model chips and unmatched
regions. Painting alone does not regenerate it.

## Week 18 painting selection

The scan-history painting buttons prepare the trimmed `progress-02-upper-clean.stl`
version and the additional lower **Fusion H4** capture. The painting controls
offer only this suggested pair; original observations remain in history. H4 is
a tentative lower painting preference because its margins appear
more compact in the existing capture comparison; it is not a validated accuracy
winner. The week-18 model-chip notes remain visible in the editor.

Earlier captures and their saved notes keep explicit source-bound links, but are
not offered in the week 18 painting picker. Each capture is verified
against its manifest SHA-256 and saves separate versioned annotations and notes:
`week-18-lower`, `week-18-lower-fusion-h-4`, and `week-18-lower-fusion-h-6` under
`.orthoplan-region-corrections/USER_ONE/`. Upper saves use `week-18-upper`.
The cleaned upper saves separately as `week-18-upper-upper-clean`.
My Notes reopens the exact saved capture. Existing original-scan saves remain valid.
These prepared surfaces start unpainted unless a matching local draft exists;
no old face labels are copied onto a different mesh. Painting does not reconstruct
missing model surfaces. Leave uncertain chip regions unreviewed.

The observed week-18 history continues to display the original pair. Choosing H4
for painting does not replace that observation or generate a week 1–18 motion fit.
After both paintings are saved and reviewed, they can be incorporated separately.

Week 18 painting uses a separate inspection camera because these model captures
have different axes from the earlier intraoral scans. Default/Face-on and the
relative Above/Side presets change only the camera, never vertex or label order.

### Cleaned upper painting version

`visits/progress-02/captures/upper-clean/progress-02-upper-clean.stl` is the
unchanged Desktop `Fusion_H_1_Upper_CLEAN.stl`, renamed on import. Its 491,548
triangles are an exact subset of the original upper’s 828,960 triangles. Source
metadata records the original hash and trimming relationship. No surfaces were
filled, moved or reconstructed. This is a derivative of the same observation,
not an additional observed visit.

The week 18 upper painting action selects this version explicitly. Historical
upper links remain valid and retain their separate hash-bound drafts. My Notes
links back to the saved version. Painting
this version does not replace the original observed-history scan or fit motion.

### Week 18 first painting sweep

The normal week 18 Upper/Lower actions now select cleaned upper / Fusion H4
lower, including entry from the visit selector. There are no alternative-capture
dropdowns. Reload and older saved-note links retain their exact source identity.

`tools/seed_week_eighteen_labels.py` projects the latest saved week 7 crown labels
onto these two surfaces using proper PCA rotation starts, trimmed rigid ICP,
distance/normal/round-trip checks, contact buffers and largest-component cleanup.
The lower model also needs translated starting positions to avoid fitting its
base instead of crowns. Scan coordinates, face order and missing surfaces remain
unchanged. This does not fit week 1–18 movement.

Private, unreviewed draft artifacts and fit reports live under
`private/painting-seeds/week-18/`. They are excluded from public releases and
static dataset serving. `--save` installs fresh local drafts; `--install-prepared --save` installs those prepared records without refitting. Both reject any existing
painting rather than replacing it. The initial sweep colors all 14 present teeth
per arch; gray includes gum/model context and weak or fragmented matches.
