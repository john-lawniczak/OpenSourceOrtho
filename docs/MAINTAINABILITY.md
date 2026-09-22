# Maintainability and Composability

OpenSource Ortho should stay modular enough that safety boundaries, mesh processing, planning logic, model adapters, and UI contracts can evolve independently.

## Design Rules

- Keep domain objects small, explicit, and serializable.
- Prefer typed data contracts over loosely shaped dictionaries.
- Keep deterministic rules separate from model providers.
- Keep visualization frame generation separate from rendering technology.
- Keep IO adapters separate from planning and evaluation.
- Add new packages only when they represent a real ownership boundary.
- Avoid hidden global state, implicit coordinate frames, and untracked units.

## File Size Guardrails

These are review triggers, not hard laws:

- Python source file target: under 250 lines.
- Python source file warning: 300 lines.
- Python source file split-required threshold: 500 lines.
- First-party JavaScript, Swift, and Kotlin warning: 300 lines.
- First-party JavaScript, Swift, and Kotlin split-required threshold: 500 lines.
- Test file target: under 300 lines.
- Function or method target: under 60 lines.
- Class target: under 150 lines.

When a file crosses a warning threshold, prefer one of these moves:

- extract a focused helper module
- split provider adapters from shared protocols
- split data models by domain
- move test fixtures into dedicated fixture modules
- move rendering concerns out of planning/evaluation packages

Do not split files only to satisfy a number. Split when it improves names, ownership, testing, or reviewability.

Existing UI/native files above the split threshold have explicit non-growth
budgets in `tools/maintainability_baseline.json`. CI fails if one grows past its
recorded ceiling. Lower or remove a budget whenever a hotspot is split; new
first-party files do not receive legacy budgets. Vendored JavaScript and test
files are excluded from this source-file line check.

## Directory Ownership

`orthoplan/model/`

- stable domain objects and settings
- no provider SDK imports
- no UI rendering code
- owns the single data-gap derivation (`model/gaps.py`) so rules and viz never duplicate gap text
- owns typed coordinate frames (`model/geometry.py`); coordinate frames are never free-form strings

`orthoplan/io/`

- import/export adapters
- no deterministic rule decisions
- no model-provider calls

`orthoplan/planning/`

- staging, setup, transforms, collision helpers
- owns cumulative pose composition (`planning/transforms.py`) and timeline projection (`planning/timeline.py`)
- viz consumes these contracts; viz must not recompute movement or rotation renderability
- no LLM calls
- no UI framework dependencies

`orthoplan/evaluation/`

- deterministic rules, findings, prompts, provider interfaces
- model outputs remain advisory and linted

`orthoplan/viz/`

- visualization data contracts and rendering adapters
- should consume `TreatmentPlan` and `StageProgressFrame`
- should not recalculate policy

`tests/`

- narrow tests near the behavior they protect
- add regression tests before broad refactors
- include safety-boundary tests for generated text and findings

## Review Checklist

Before committing, ask:

- Did this change keep safety, planning, IO, provider, and UI responsibilities separate?
- Are movement units and coordinate frames explicit?
- Did any model/provider code bypass deterministic linting?
- Did any UI or docs imply approval or readiness?
- Did any file grow large enough that future edits will become harder?
- Are tests focused on the behavior that could regress?

## Automation

Run:

```bash
python3 tools/check_maintainability.py
```

Use strict mode in CI or before large commits. Strict mode covers Python
structure plus first-party JavaScript, Swift, and Kotlin line budgets:

```bash
python3 tools/check_maintainability.py --strict
```
