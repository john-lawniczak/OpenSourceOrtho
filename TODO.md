# TODO

## Next Major Implementation Items

### 1. Measurement Truth Lab

Build the full measurement-validation harness described in
[ACQUISITION_ADVISOR_PLAN.md](ACQUISITION_ADVISOR_PLAN.md).

Target outcomes:

- synthetic STL fixtures with known bounds, transforms, and hashes
- expected stage-frame outputs with mm/degree tolerances
- fixture families for bounds/scale, cumulative movement, rotation/frame gating,
  segmentation linkage, movement caps, and report reproducibility
- CLI command such as `orthoplan measurement-lab`
- report embedding for validation status
- e2e/visual checks that compare expected vs actual UI movement behavior

Definition of done:

- at least one fixture in every planned fixture family
- failures produce precise mismatch messages
- no patient data
- all checks pass in CI

### 2. Acquisition Advisor Follow-Through

The deterministic acquisition advisor is implemented, but the next pass should polish it into
a stronger user-facing workflow.

Target outcomes:

- richer UI presentation for resolve/surface/close effects
- `plan-summary` includes a concise acquisition-advice summary
- optional JSON output for `orthoplan acquisition`
- clearer report section for acquisition advice
- additional tests for multi-scan unit confirmation and edge cases
- screenshot regeneration showing the Acquire Next panel

Definition of done:

- acquisition advice is understandable to a new user without reading docs
- every string remains verdict-free
- no model/LLM output can override deterministic findings

## Product Readiness Push Toward 9/10

Raise the application toward a 9/10 research/developer-preview readiness score in these
domains:

- **Measurement accuracy:** comprehensive Measurement Truth Lab, strict tolerances,
  golden fixtures, and reproducible reports.
- **Visualization trust:** schematic mode remains honest; real mesh mode/export should be
  gated on validated segmentation and scale.
- **Print/export handoff:** move from readiness metadata to actual file packaging only after
  geometry generation, hashes, material/process caveats, and clinician-supervised workflow
  boundaries are solid.
- **UI quality:** improve onboarding, empty/error states, stage editing ergonomics, visual
  regression tests, and report/export affordances.
- **Safety invariants:** keep verdict-free/property-style tests broad and mandatory.
- **Documentation:** keep HOW_TO, SAFETY, CLI walkthrough, architecture, and prompt docs aligned
  with shipped behavior.

## Current Non-Goals

- Do not claim clinical approval or diagnosis.
- Do not imply users can safely manufacture or wear aligners from the app alone.
- Do not add LLM/sub-agent output that bypasses deterministic linting and quarantine.
