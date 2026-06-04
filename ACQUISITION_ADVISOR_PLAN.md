# Implementation Plan — Acquisition Advisor (deterministic data-gap impact)

> **Status:** implemented in `orthoplan/evaluation/acquisition.py`.
> **Owner module:** `orthoplan/evaluation/acquisition.py`.
> **One-liner:** Turn the passive "data gaps" list into deterministic decision
> support: for each missing data modality, compute exactly which deterministic
> findings it would *resolve* and which currently-suppressed checks it would
> *unlock*, then rank "what to acquire next" — without diagnosing anything.

---

## 1. Problem & why this is the right feature

The toolkit is already obsessive about *what it does not know* — `data_gaps(plan)`
lists missing modalities, and rules like `evaluate_root_sensitive_movement` warn
when root/CBCT data is absent. But that knowledge is **passive**: it tells a user
data is missing, not what difference acquiring it would make.

The Acquisition Advisor computes the **marginal information value** of each
missing modality by re-running the existing deterministic engine against a
counterfactual plan in which that one gap is "filled," then diffing the result.
It is decision support for *data acquisition* ("CBCT would let the engine assess
3 currently-unassessable movements"), never a clinical recommendation.

This is high-leverage because it is:
- **Deterministic & pure** — a function over `run_rules` + `data_gaps`; no model, no new clinical claims.
- **Accretive** — reuses the engine, the `DataAvailability` model, and the scale gate verbatim. New deterministic rules automatically participate.
- **On-mission & safe-by-construction** — it advises which *data* to get; it never predicts what that data would show.

---

## 2. Core concept — counterfactual marginal impact

For one missing modality `m`, build `plan_m` = the plan with `m` toggled to
"available," run the engine on both, and diff:

```
baseline_findings   = run_rules(plan)
baseline_gaps       = data_gaps(plan)
counterfactual      = run_rules(plan_m)

resolved   = baseline_findings - counterfactual   # findings that exist *because* m is missing
surfaced   = counterfactual - baseline_findings   # checks unlocked by having m (may add findings!)
closed_gaps = baseline_gaps - data_gaps(plan_m)    # gap-list entries m removes
```

Two distinct, equally important effects:

1. **Resolves** — a gap-driven finding disappears (e.g., filling `roots` clears
   the root-sensitive WARNING because the *absence of data* warning no longer applies).
2. **Unlocks** — filling a gap lets a previously **suppressed** rule run, which
   can **surface new findings**. The flagship case: a plan with unverified scan
   units suppresses movement-cap evaluation (the cap rule returns only a NOTICE);
   confirming units unlocks the per-stage cap checks, *surfacing* the cap findings
   that were hidden. "Unlocks" is a feature, not noise — it reveals what you
   currently cannot see.

This effect split is the heart of the feature and must be preserved in the UI/CLI copy.

---

## 3. Safety & honesty constraints (non-negotiable)

These are what keep the feature inside the project's boundary. Each maps to a test.

1. **"Resolved" ≠ "safe."** Toggling `roots=True` does not supply root geometry;
   it only tells the engine to assume the data exists, which clears the
   *absence-of-data* warning. Copy MUST say "the engine would no longer flag the
   absence of this data" / "would become assessable," never "would be safe/acceptable."
2. **No fabrication.** The counterfactual only flips *availability* (a boolean,
   or scan-units confirmed). It never invents movement values, geometry, or rule outcomes.
3. **Acquisition advice, not clinical advice.** Output describes which data to
   acquire and what the *engine* could then assess. It never tells a clinician
   what to do clinically and never diagnoses.
4. **Verdict-free.** All generated strings must pass the existing verdict-word
   check (`orthoplan.evaluation.finding._VERDICT_RE`). A test asserts this over
   every string the advisor can emit.
5. **Never raises.** Like `evaluate_plan_payload` and `request_advisory`, the
   advisor returns results as data and tolerates odd plans (no stages, no scans).
6. **Single source of truth.** It calls `run_rules` — it does NOT reimplement any
   rule logic. New rules and new gap-dependencies are reflected automatically.

---

## 4. Modality model — what counts as a fillable gap

The advisor enumerates **applicable** modalities only (a gap that is already
satisfied is not advice).

| Modality key | Toggle applied to the counterfactual plan | Applicable when |
|---|---|---|
| `roots` | `data.roots = True` | `not data.roots` |
| `cbct` | `data.cbct = True` | `not data.cbct` |
| `periodontal_status` | `data.periodontal_status = True` | `not data.periodontal_status` |
| `occlusion_scan` | `data.occlusion_scan = True` | `not data.occlusion_scan` |
| `segmented_teeth` | `data.segmented_teeth = True` | `not data.segmented_teeth` |
| `photos` | `data.photos = True` | `not data.photos` |
| `radiographs` | `data.radiographs = True` | `not data.radiographs` |
| `clinician_notes` | `data.clinician_notes = True` | `not data.clinician_notes` |
| `scan_units_confirmed` | every `scan.asset.units = MeshUnits.MM` | plan has scans AND `not plan.scale_confirmed` |

Notes:
- `scan_units_confirmed` models **"units confirmed,"** not "the units are mm." The
  *value* is irrelevant to which rules run (only confirmed-vs-unverified gates the
  cap rule); MM is an arbitrary confirmed sentinel, documented as such.
- Modalities with **no current rule dependency** (e.g. `photos`, `radiographs`)
  will show "closes a data-gap entry; no deterministic finding currently depends
  on it." That is honest and useful — it tells the user this modality changes no
  automated check today.
- Counterfactual plans are built with `model_copy(update=...)` (nested for `data`
  and `scans`); the toggles keep the plan valid by construction.

---

## 5. Data model (proposed)

In `orthoplan/evaluation/acquisition.py` (pydantic, JSON-serializable, frozen where natural):

```python
class FindingRef(BaseModel):          # stable, content-based identity for diffing
    severity: str
    category: str
    title: str

class GapImpact(BaseModel):
    modality: str                     # e.g. "cbct"
    label: str                        # human label, e.g. "CBCT (3D root/bone imaging)"
    acquisition: str                  # what to acquire, plain language
    resolves: list[FindingRef]        # findings that would clear (absence-of-data warnings)
    surfaces: list[FindingRef]        # findings unlocked by enabling a suppressed rule
    closes_data_gaps: list[str]       # data_gaps() entries removed
    unlocks_assessment: bool          # True if a previously-suppressed rule now runs
    priority_score: float             # deterministic, heuristic ranking weight (NOT clinical priority)
    note: str                         # caveat-bearing, verdict-free explanation

class AcquisitionAdvice(BaseModel):
    baseline_finding_count: int
    baseline_data_gaps: list[str]
    impacts: list[GapImpact]          # sorted by priority_score desc, then modality asc
    caveat: str                       # standing safety caveat (see §3)
```

`finding_key(finding) -> tuple` = `(severity, category, title, message)` — fully
content-based so diffs are deterministic and order-independent. `FindingRef` keeps
the first three for display; the message is part of the key but not surfaced.

**Priority score (deterministic, clearly heuristic, labeled):**
```
SEVERITY_WEIGHT = {"warning": 3, "notice": 2, "info": 1}
priority = sum(SEVERITY_WEIGHT[f.severity] for f in resolves)
         + sum(SEVERITY_WEIGHT[f.severity] for f in surfaces)
         + len(closes_data_gaps) * 0.5
```
Documented as a ranking heuristic for "what changes the most," **not** a clinical
priority. Weights live as module constants so they are inspectable/configurable.

---

## 6. Algorithm

```
def acquisition_advice(plan) -> AcquisitionAdvice:
    baseline_findings = run_rules(plan)
    baseline_keys     = { finding_key(f): f for f in baseline_findings }
    baseline_gaps     = data_gaps(plan)
    impacts = []
    for modality in applicable_modalities(plan):       # §4
        plan_m = apply_toggle(plan, modality)
        cf_findings = run_rules(plan_m)
        cf_keys     = { finding_key(f): f for f in cf_findings }
        resolved = [baseline_keys[k] for k in baseline_keys.keys() - cf_keys.keys()]
        surfaced = [cf_keys[k]       for k in cf_keys.keys() - baseline_keys.keys()]
        closed   = [g for g in baseline_gaps if g not in data_gaps(plan_m)]
        impacts.append(GapImpact(... unlocks_assessment = bool(surfaced) ...))
    impacts.sort(key=lambda i: (-i.priority_score, i.modality))
    return AcquisitionAdvice(..., impacts=impacts, caveat=ACQUISITION_CAVEAT)
```

Complexity: `O(modalities × cost(run_rules))`; modalities ≤ 9 and `run_rules` is
cheap, so it is negligible.

---

## 7. Module layout & ownership

- **New:** `orthoplan/evaluation/acquisition.py` — models + `acquisition_advice(plan)`
  + `applicable_modalities` + toggles + priority. Imports `run_rules`
  (`evaluation.engine`), `data_gaps` (`model.gaps`), `MeshUnits` (`model.assets`),
  `TreatmentPlan` (`model.plan`). No import cycle (evaluation already sits above model;
  nothing imports `acquisition`).
- **Export:** add the public names to `orthoplan/evaluation/__init__.py`.
- **No new clinical claims**, so this is NOT a `Finding`/rule and does not emit
  through `lint_finding` — but its strings are verdict-checked by test (§3.4).
- Keep the module under the 250-line maintainability target; split toggles into a
  small `_MODALITIES` table if it grows.

---

## 8. Surfaces (phased)

### CLI — `orthoplan acquisition <plan.json>`
(`advise` is already the LLM layer, so this is a distinct verb.) Prints the
baseline, then each modality ranked, e.g.:

```
Acquisition advisor for: Synthetic example - basic staged plan
Baseline: 2 findings, 5 data gaps. (This estimates what the ENGINE could assess
if data were available; it is not a clinical recommendation and predicts nothing
about what the data would show.)

1. CBCT (3D root/bone imaging)  [score 3.0]
   - Would clear 1 finding flagged only because root/bone data is absent:
       WARNING: Root-sensitive movement planned without root or bone imaging
   - Closes data gap: "CBCT unavailable"
2. Confirm scan units            [score 3.0]
   - Would unlock movement-cap evaluation, surfacing 1 currently-hidden check.
...
```

Reuse the clean error handling pattern already in `cli.py` (read errors → exit 2).

### HTTP API
Add `acquisition_advice` to the `evaluate_plan` response dict (the UI already
consumes that single call), serialized via `AcquisitionAdvice.model_dump()`.
Alternatively a dedicated function; integrating into `evaluate_plan` keeps the UI
to one round-trip. Add an `api`-level test asserting the key is present and shaped.

### UI
A read-only **"What to acquire next"** panel beside the existing **Data Gaps**
panel (sidebar). Renders `acquisition_advice.impacts`: modality label, the
resolve/surface/close effects, and the standing caveat. Pure render of engine
output (consistent with "UI never reimplements the engine"). Escape all dynamic
strings (existing `escapeHtml`). Add to the headless screenshot.

---

## 9. Milestones & acceptance criteria

**B1 — Core engine (no surface).** `evaluation/acquisition.py` + models + unit
tests. *Done when:* `acquisition_advice(plan)` is deterministic, never raises,
and the diff semantics (resolves/surfaces/closes) are covered by tests.

**B2 — CLI + HTTP API.** `orthoplan acquisition` command; `acquisition_advice` in
the `evaluate_plan` response. *Done when:* CLI runs on both example plans with
real output, exits 2 cleanly on bad input, and an api test asserts the response shape.

**B3 — UI panel.** "What to acquire next" panel + screenshot regeneration.
*Done when:* the panel renders from `/api/evaluate`, escapes input, shows the
caveat, and the e2e smoke still passes.

**B4 — Docs & safety.** `docs/CLI_WALKTHROUGH.md` section, `docs/SAFETY.md`
note (the "resolved ≠ safe" framing), `Dev_history.md`, plan progress. *Done when:*
docs match behavior and the verdict-free test passes.

Each milestone is independently shippable, CI-gated, and committed separately.

---

## 10. Testing strategy

- **Diff semantics:** filling `roots` (or `cbct`) resolves the root-sensitive
  WARNING; filling `segmented_teeth` resolves the segmentation NOTICE.
- **Unlock/surface:** a plan with an unverified-units scan and an
  over-cap movement → `scan_units_confirmed` has `unlocks_assessment=True` and
  `surfaces` the cap finding that was hidden by the scale gate.
- **No-dependency gap:** filling `photos` closes the (none, since photos isn't in
  `data_gaps`) — confirm it reports "no deterministic finding depends on it" and
  only closes a gap entry if one exists. (Audit which flags appear in `data_gaps`;
  `periodontal_status`/`occlusion_scan`/`clinician_notes` do, `photos`/`radiographs` do not.)
- **Applicability:** already-available modalities are absent from `impacts`;
  `scan_units_confirmed` absent when there are no scans or scale already confirmed.
- **Determinism:** same plan → byte-identical `model_dump()`; ordering stable.
- **Safety:** every emitted string (labels, acquisitions, notes, caveat) is
  verdict-free (reuse `_VERDICT_RE`); the advisor never raises on empty / no-op /
  scan-only plans.
- **Engine-coupling guard:** a test that adds a throwaway gap-dependent rule (or
  asserts the existing ones) proves new rules participate automatically.

Target: parity with existing modules' rigor (positive + negative + edge cases).

---

## 11. Edge cases

- Plan with no stages / all-zero movement → baseline findings minimal; advisor
  still lists gap-closing modalities; no crash.
- Plan with everything already available → `impacts == []` (nothing to advise).
- Multiple scans, mixed units → `scan_units_confirmed` confirms *all* scans.
- Filling a gap that both resolves AND surfaces (rare today, possible later) →
  both lists populated; `note` explains the net effect honestly.
- `model_copy` does not re-run validators; toggles are validity-preserving, but a
  defensive `TreatmentPlan.model_validate(plan_m.model_dump())` may be used if we
  want hard guarantees (decide in B1; default: trust the toggle).

---

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| "Resolved" read as "safe" | Copy + caveat + verdict-free test; the word "resolve" is scoped to "absence-of-data flag clears." |
| Implies the data's *content* is predicted | Caveat on every output; only availability is toggled; documented in SAFETY.md. |
| Finding diff fragility | Content-based `finding_key` (severity+category+title+message); determinism test. |
| Combinatorial blow-up | v1 is **single-gap marginal** only; multi-gap "bundles" deferred to a future v2 with an explicit note that interactions exist. |
| Drift from rules | Advisor calls `run_rules`; never copies rule logic; engine-coupling test. |
| UI overstating authority | Panel is observational, caveat-bearing, sits next to Data Gaps, no verdict styling. |

---

## 13. Non-goals (v1)

- No diagnosis, no clinical prioritization, no prediction of what acquired data shows.
- No multi-gap combinatorial bundles (single-modality marginal impact only).
- No cost/time/$ modeling of acquisition.
- No model/LLM involvement (deterministic only; the LLM layer may later *explain*
  the deterministic advice, gated by lint — out of scope here).

---

## 14. Open questions (resolve before/while implementing)

1. **CLI verb:** `acquisition` vs `advise-data` vs folding a short summary into
   `plan-summary`. (Proposed: dedicated `acquisition`, plus a one-line count in
   `plan-summary`.)
2. **API placement:** embed in `evaluate_plan` (one round-trip, simplest for the
   UI) vs a separate endpoint. (Proposed: embed.)
3. **Re-validate counterfactuals?** Trust the toggle (fast) vs round-trip through
   `model_validate` (paranoid). (Proposed: trust; revisit if a future toggle is non-trivial.)
4. **Priority weights:** are the §5 weights acceptable as the labeled default, or
   should they be configurable via settings? (Proposed: module constants for v1.)

---

## 15. Definition of done (whole feature)

- `acquisition_advice(plan)` is pure, deterministic, never raises, verdict-free,
  and reflects the live rule set with no duplicated logic.
- Reachable from CLI and the UI; the UI renders it beside Data Gaps with the caveat.
- "Resolved ≠ safe" and "availability-only, not content" are stated in SAFETY.md
  and enforced by tests.
- All suites green in CI (Python, JS, e2e); maintainability `--strict` passes.
- Docs (CLI walkthrough, SAFETY, plan, Dev_history) updated in the same change set.

---

# Companion Implementation Plan - Measurement Truth Lab

> **Status:** partially seeded; needs full implementation.
> **Owner module (proposed):** `orthoplan/validation/measurement_lab.py`.
> **One-liner:** Build a reproducible benchmark harness that proves OpenSource Ortho
> recovers known geometric measurements from synthetic STL fixtures, known transforms,
> expected movement/cap outputs, and explicit tolerances.

---

## A. Problem & why this is the right companion feature

The Acquisition Advisor improves data sufficiency, but the project also needs proof that
the measurements it does make are correct. The current test suite has seed coverage for
cumulative movement, movement caps, STL bounds, and PCA tolerance. That is not yet a full
measurement-validation lab.

The Measurement Truth Lab should become the project’s public evidence layer:

- synthetic fixtures with known geometry and no patient data
- known transforms applied to known tooth-like meshes
- expected millimeter/degree outputs with tolerances
- canonical reports that bind fixture input hashes to engine output
- visual snapshots that prove schematic/mesh renderers show the expected movement

This is the fastest path from "credible prototype" to "serious research tool."

---

## B. Core concept - fixture -> transform -> expected output

Each lab case is a structured fixture:

```python
class MeasurementTruthCase(BaseModel):
    id: str
    description: str
    fixture_kind: Literal["stl", "plan", "segmented_mesh"]
    input_assets: list[MeshAsset]
    plan: TreatmentPlan
    expected_frames: list[ExpectedStageFrame]
    expected_findings: list[ExpectedFinding]
    tolerances: MeasurementTolerances
```

The harness runs the normal engine path:

```
case.plan -> evaluate_plan(plan)
          -> build_stage_progress_frames(plan)
          -> run_rules(plan)
          -> optional handoff report
```

Then it compares actual outputs to the expected values. Nothing gets a special validation-only
code path. The lab must use the same public API that the CLI/UI/reporting use.

---

## C. Fixture families

### C1. Bounds and scale fixtures

Purpose: prove STL import reads vertices, face count, bounding boxes, scale warnings, and
unit-confirmation gates correctly.

Cases:

- ASCII STL with known min/max bounds
- binary STL with known min/max bounds
- degenerate triangle fixture
- implausible mm span fixture
- unverified-units fixture that suppresses cap evaluation
- confirmed-units fixture that unlocks cap evaluation

Expected outputs:

- vertex count
- face count
- bounding box min/max
- max span
- mesh quality notes
- `scale_confirmed`
- movement-cap finding presence/absence

### C2. Cumulative translation fixtures

Purpose: prove staged translation is exact vector summation.

Cases:

- single tooth, multiple stages
- multiple teeth with independent stage histories
- positive/negative x/y/z movement
- zero-delta stages
- gapped UI stage inputs reindexed to contiguous model stages

Expected outputs:

- exact cumulative `translate_x_mm`, `translate_y_mm`, `translate_z_mm`
- per-stage frame order
- stable tooth sorting

### C3. Rotation and coordinate-frame fixtures

Purpose: prove rotation values are reported honestly and rendered only when eligible.

Cases:

- scan-local frame: rotation values present, `rotation_renderable=False`
- approximate PCA frame: `tooth_frames` populated, `rotation_renderable=False`
- trusted anatomical frame: `rotation_renderable=True`
- global anatomical frame with mesiodistal/buccolingual/occlusogingival axes
- mismatched coordinate frame rejected by the model

Expected outputs:

- rotation component totals
- `rotation_renderable` flags
- trusted vs approximate frame behavior
- validation errors for unsafe frame mixing

### C4. Segmentation linkage fixtures

Purpose: prove mesh/tooth identity cannot drift.

Cases:

- delta references its own segmented mesh
- delta references another tooth’s mesh -> validation error
- duplicate segmented mesh content -> import error
- duplicate mesh asset IDs -> validation error
- segmentation present suppresses abstract-proxy data-gap finding

Expected outputs:

- validation errors
- `segmented_tooth_values`
- segmentation notices present/absent
- artifact provenance

### C5. Rule/cap fixtures

Purpose: prove cap math and finding vocabulary remain stable.

Cases:

- horizontal Euclidean cap (`sqrt(x^2 + y^2)`)
- vertical cap independent of horizontal movement
- tip/torque angular cap
- long-axis rotation cap
- per-tooth cap override
- unverified-units suppression and confirmed-units surfacing

Expected outputs:

- finding title/category/severity
- cap reference
- data gap and clinician question fields
- numeric formatting tolerance

### C6. Report reproducibility fixtures

Purpose: prove lab cases can be handed off and replayed.

Cases:

- same plan -> same plan hash and evaluation hash
- changed movement -> changed evaluation hash
- reviewer metadata included
- optional HMAC signature present and stable for fixed timestamp/key

Expected outputs:

- `plan.sha256`
- `evaluation_sha256`
- `report_sha256`
- signature fields

---

## D. Data model and module layout

Proposed files:

- `orthoplan/validation/__init__.py`
- `orthoplan/validation/measurement_lab.py`
- `tests/fixtures/measurement_truth/` (generated or checked-in tiny synthetic STLs)
- `tests/test_measurement_truth_lab.py`

Suggested models:

```python
class MeasurementTolerances(BaseModel):
    linear_mm: float = 1e-6
    angular_deg: float = 1e-6
    bounds_mm: float = 1e-6

class ExpectedToothPose(BaseModel):
    tooth: str
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0
    translate_z_mm: float = 0.0
    rotate_tip_deg: float = 0.0
    rotate_torque_deg: float = 0.0
    rotate_rotation_deg: float = 0.0
    rotation_renderable: bool = False

class ExpectedStageFrame(BaseModel):
    stage_index: int
    poses: list[ExpectedToothPose]

class MeasurementTruthResult(BaseModel):
    case_id: str
    passed: bool
    failures: list[str]
```

The harness should be pure Python and dependency-light. If optional mesh libraries are used,
cases must skip cleanly when the optional dependency is unavailable.

---

## E. CLI and report surface

Add:

```bash
orthoplan measurement-lab
orthoplan measurement-lab --case bounds-known-ascii
orthoplan measurement-lab --json
```

Output should show:

- case ID
- fixture hashes
- pass/fail status
- tolerance used
- exact mismatches

Reports should optionally embed a compact `measurement_lab` section:

```json
{
  "case_id": "golden-translation-001",
  "passed": true,
  "tolerances": {"linear_mm": 0.000001}
}
```

---

## F. UI / visual regression surface

The UI does not need a full lab dashboard at first. Useful v1:

- show measurement-lab status in docs and reports
- add Playwright visual regression snapshots for:
  - stage editing changes movement
  - 2D canvas has expected non-background pixels
  - 3D canvas mounts
  - invalid input shows API rejection state
  - acquisition panel renders

Future v2:

- a read-only "Validation" panel showing fixture pass/fail
- downloadable validation report
- visual overlays comparing expected vs actual stage positions

---

## G. Acceptance criteria

1. At least one fixture in each family C1-C6.
2. Fixture outputs compare against tolerances, not broad string snapshots.
3. No patient data; every fixture is synthetic and documented.
4. The lab uses public engine/API/report functions, not duplicated logic.
5. Failing cases produce actionable mismatch messages.
6. `pytest`, JS tests, maintainability, and e2e smoke/visual regression remain green.
7. Docs describe the lab as evidence of geometric correctness, not clinical validity.

---

## H. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Lab becomes a parallel engine | Use existing public API only; no duplicated movement logic. |
| Synthetic fixtures overfit simple geometry | Include multiple fixture families and future real-world open datasets when legally safe. |
| Tolerances hide real errors | Keep strict defaults; require explicit tolerance per case. |
| Visual tests become flaky | Prefer deterministic camera/viewport and pixel-count assertions before full screenshot diffs. |
| Users confuse measurement proof with clinical proof | Docs must say this proves geometric calculations only. |

---

## I. Next implementation sequence

1. Create `orthoplan/validation/measurement_lab.py` with models, runner, and two cases:
   known STL bounds + cumulative translation.
2. Add CLI `orthoplan measurement-lab`.
3. Add fixture family coverage C1-C6.
4. Add report embedding for lab status.
5. Add Playwright visual regression snapshots.
6. Update docs and `TODO.md` when complete.
