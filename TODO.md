# TODO

## Next Major Implementation Items

### 1. Measurement Truth Lab Expansion

Version 1 is implemented as `orthoplan measurement-lab` with seed cases for each planned
fixture family. The next pass should expand it into the full validation harness described
in [ACQUISITION_ADVISOR_PLAN.md](ACQUISITION_ADVISOR_PLAN.md).

Target outcomes:

- synthetic STL fixtures with known bounds, transforms, and hashes
- expected stage-frame outputs with mm/degree tolerances
- fixture families for bounds/scale, cumulative movement, rotation/frame gating,
  segmentation linkage, movement caps, and report reproducibility
- CLI command `orthoplan measurement-lab`
- report embedding for validation status
- e2e/visual checks that compare expected vs actual UI movement behavior

Definition of done:

- at least one fixture in every planned fixture family
- failures produce precise mismatch messages
- no patient data
- all checks pass in CI

### 2. Acquisition Advisor Follow-Through

The deterministic acquisition advisor is implemented in the engine, API, UI, CLI, and
`plan-summary`. The next pass should polish it into a stronger user-facing workflow.

Target outcomes:

- richer UI presentation for resolve/surface/close effects
- deeper report integration for acquisition advice
- richer edge-case coverage around multi-scan unit confirmation
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
- **Print/export handoff:** keep improving actual file packaging, geometry generation, hashes,
  material/process caveats, and user-responsibility boundaries.
- **UI quality:** improve onboarding, empty/error states, stage editing ergonomics, visual
  regression tests, and report/export affordances.
- **Safety invariants:** keep verdict-free/property-style tests broad and mandatory.
- **Documentation:** keep HOW_TO, SAFETY, CLI walkthrough, architecture, and prompt docs aligned
  with shipped behavior.

## Current Non-Goals

- Do not claim approval, diagnosis, or guaranteed safety.
- Do not imply generated files guarantee fit, suitability, or risk-free physical use.
- Do not add LLM/sub-agent output that bypasses deterministic linting and quarantine.
