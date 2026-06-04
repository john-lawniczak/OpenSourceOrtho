# Contributing to OpenSource Ortho

Thanks for helping. This is a **safety-boundary-first research toolkit**, not a
medical device. Before contributing, read [docs/SAFETY.md](docs/SAFETY.md) and
[docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md).

## Setup

```bash
git clone https://github.com/john-lawniczak/OpenSourceOrtho
cd OpenSourceOrtho
python -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -e ".[dev]"
```

## Running the checks (the same ones CI runs)

```bash
pytest -q                                   # Python tests
python tools/check_maintainability.py --strict   # file/function size + ownership
cd ui && node --test                        # JS unit tests (Node 18+)
```

Optional end-to-end 3D-viewer smoke (headless browser):

```bash
pip install -e ".[e2e]" && python -m playwright install chromium
pytest tests/e2e -q
```

Run the app locally:

```bash
orthoplan serve            # then open http://127.0.0.1:8000
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of the above
on every push and pull request. PRs should be green before review.

## Non-negotiable rules

These are enforced by code and review, not just convention:

1. **No patient data, ever.** Fixtures and examples are synthetic. Uploaded STL
   bytes are never stored or committed; only redacted metadata is kept.
2. **No verdict language.** Findings must not state or imply a plan is "safe",
   "approved", "cleared", "acceptable", or that a patient is a "good candidate".
   `lint_finding()` is the single gate and scans every text field.
3. **Deterministic rules own mechanics.** Model-sourced (LLM) findings may only
   comment on data gaps, education, or clinician questions, and must pass
   `lint_finding()` (they are quarantined, not crashed, on failure).
4. **Geometry, not biomechanics.** The toolkit models crown-surface geometry
   only. Do not infer roots, bone, periodontal status, or treatment feasibility.
   The per-tooth PCA frame is an approximate visualization aid, not anatomy.
5. **The UI never reimplements the engine.** It sends plan JSON to
   `POST /api/evaluate` and renders what `orthoplan.api.evaluate_plan` returns.
   Add evaluation logic to the Python engine, not to JavaScript.
6. **Units and coordinate frames are explicit.** No implicit mm/degrees, no
   free-form coordinate-frame strings.

## Module ownership

| Package | Owns | Must not |
|---------|------|----------|
| `orthoplan/model/` | domain objects, settings, geometry, data gaps | import provider SDKs or UI code |
| `orthoplan/io/` | import/export adapters | make clinical decisions or call providers |
| `orthoplan/planning/` | transforms, timeline, per-tooth frame | call LLMs or depend on a UI framework |
| `orthoplan/evaluation/` | deterministic rules, findings, lint, providers | let model output bypass linting |
| `orthoplan/viz/` | progress-frame contracts | recompute movement/policy |
| `ui/` | browser UI; `core.js` holds DOM-free, tested logic | reimplement the engine |

New deterministic rules register in `orthoplan/evaluation/engine.py`.

## Commits

- Keep changes focused; add tests for new behavior and regressions.
- Update [docs/Dev_history.md](docs/Dev_history.md) when you change behavior, and
  [docs/OpenAI_Agents.md](docs/OpenAI_Agents.md) when you change provider behavior.
- Respect the file-size guardrails in MAINTAINABILITY.md.

## Dependencies

New dependencies must be permissively licensed and recorded in
[docs/LICENSE_AUDIT.md](docs/LICENSE_AUDIT.md). Prefer the standard library;
heavy or optional dependencies go behind an extra in `pyproject.toml`.
