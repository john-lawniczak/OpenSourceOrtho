# Contributing to OpenSource Ortho

Thanks for helping. This is a **safety-boundary-first clear-aligner planning
playground and research toolkit**, not a medical device and not complete
treatment-planning software. Before contributing, read [docs/SAFETY.md](docs/SAFETY.md)
and [docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md).

## Patients: donate your own scans

Patients can contribute their own existing scans to help develop and evaluate
this clear-aligner planning safety playground and research toolkit. Before/after
and progress scans are especially useful; a single scan pair also helps.
`USER_ONE` is the first tracked donor case.

Start with the [patient donation guide](docs/PATIENT_DATA_DONATION.md), including
a records-request template and the [consent form](docs/DATA_DONATION_CONSENT.md).
Choose **CC0 1.0 or CC BY 4.0** only for files you have authority to license.
Review privacy and redistribution rights before any public upload. The guide
explains how to propose a contribution without attaching health records, then
submit a reviewed bundle. Raw CBCT/DICOM and identifying paperwork stay local.
We work with donors on best-effort de-identification before publication; anonymity
cannot be guaranteed. Private, unpublished donations can be withdrawn. Publicly
released copies and valid open-license permissions cannot reliably be recalled.

## Setup

```bash
git clone https://github.com/<your-org-or-user>/OpenSourceOrtho
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

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs one inexpensive
Linux job on non-draft pull requests: Ruff, the generated catalog, maintainability,
and JavaScript unit tests. It does not run on branch pushes or merges. Updates to
an open non-draft PR still run that quick job; newer updates cancel obsolete runs.
Draft PRs skip automatic jobs until marked ready for review.

Python tests, Open3D, motion/ML/volume tests, and Playwright are **manual only**.
In GitHub Actions, choose **CI → Run workflow**, select the branch, and choose
`python`, `geometry`, `browser`, or `all`; the default `quick` runs only the cheap
checks. Native mobile checks are separately manual with an iOS/Android/both choice.
Manual dispatch becomes available once these workflow definitions reach the default
branch. No schedules or automatic full-suite runs are configured.

Run the relevant tests locally before requesting review. For releases, validate the
full matrix locally or dispatch it explicitly; a green quick check alone does not
mean the full suite ran. See [the release workflow](docs/PRIVATE_DEVELOPMENT.md).

## Non-negotiable rules

These are enforced by code and review, not just convention:

1. **No identifying or unconsented patient records.** Patient-derived datasets
   require privacy review, documented publication consent, redistribution rights,
   and individual `consent.json` asset entries. New donations also need explicit
   data-license terms. Keep raw DICOM and identifying paperwork local/ignored.
   Use synthetic reproductions in bug reports. Contribution registration writes
   metadata locally; it does not upload scan bytes. See the
   [data guide](docs/DATA_CONTRIBUTION.md).
2. **No verdict language.** Findings must not state or imply a plan is "safe",
   "approved", "cleared", "acceptable", or that a patient is a "good candidate".
   `lint_finding()` is the single gate and scans every text field.
3. **Deterministic rules own mechanics.** Model-sourced (LLM) findings may only
   comment on data gaps, education, or clinician questions, and must pass
   `lint_finding()` (they are quarantined, not crashed, on failure).
4. **Geometry, not biomechanics.** The toolkit models crown-surface geometry
   only. Do not infer roots, bone, periodontal status, or treatment feasibility.
   The per-tooth PCA frame is an approximate visualization aid, not anatomy.
5. **Own-risk physical use only.** Do not state or imply that generated files,
   printed models, thermoformed aligners, materials, post-processing, or any
   physical use is safe, validated, legal, effective, or suitable. Outputs are
   informational geometry artifacts; users are responsible for their own use,
   manufacturing, professional supervision, and regulatory obligations.
6. **The UI never reimplements the engine.** It sends plan JSON to
   `POST /api/evaluate` and renders what `orthoplan.api.evaluate_plan` returns.
   Add evaluation logic to the Python engine, not to JavaScript.
7. **Units and coordinate frames are explicit.** No implicit mm/degrees, no
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

## Branches

Never commit to `main`. Branch from an up-to-date `main`, using a
`type/short-description` name that matches your change type:

```bash
git switch main && git pull
git switch -c fix/movement-cap-zero-division
# ...work, commit...
git push -u origin fix/movement-cap-zero-division
```

| Prefix | Use for |
|--------|---------|
| `fix/` | bug fixes |
| `feat/` | new functionality |
| `docs/` | documentation only |
| `refactor/` | behavior-preserving restructuring |
| `test/` | tests only |
| `perf/` | performance work |
| `chore/` | build, deps, tooling |

## Commit messages and PR titles

We are lighter than security-critical projects, but we keep submissions
**canonical and structured** so history is skimmable. Prefix every commit subject
and PR title with a type tag, then an imperative summary:

```
Fix: reject zero movement caps before division
Add: live OpenAI chat connector with egress consent
Docs: document the print-package manifest schema
```

| Tag | Meaning |
|-----|---------|
| `Add:` | a new feature, rule, endpoint, or file |
| `Fix:` | a bug fix |
| `Change:` | a behavior change that is neither purely add nor fix |
| `Remove:` | deletion of code, a feature, or a dependency |
| `Refactor:` | internal restructuring with no behavior change |
| `Docs:` | documentation only |
| `Test:` | tests only |
| `Perf:` | performance only |
| `Build:` | CI, packaging, tooling, dependencies |

Rules of thumb:

- One logical change per PR. Split unrelated work.
- Keep the subject under ~72 characters, imperative mood ("Add", not "Added").
- Add tests for new behavior and for any regression you fix.
- Summarize behavior changes in the PR description; update
  [docs/OpenAI_Agents.md](docs/OpenAI_Agents.md) when you change provider behavior.
- Respect the file-size guardrails in MAINTAINABILITY.md.

## Pull requests

Open the PR against `main`. The template
([.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)) asks you to
confirm:

- [ ] PR title uses a type tag (`Add:`, `Fix:`, ...).
- [ ] `pytest -q`, `python tools/check_maintainability.py --strict`, and
      `cd ui && node --test` all pass locally.
- [ ] New behavior and regressions have tests.
- [ ] No identifying or unconsented patient records; dataset additions have
      reviewed consent, rights, and explicit asset scope.
- [ ] No verdict language; mechanics stay in deterministic rules.
- [ ] Docs updated if behavior or provider behavior changed.

Maintainers may ask for changes to keep the codebase composable; small,
well-scoped PRs are reviewed fastest.

By submitting a contribution you agree it is licensed under the project's
[GNU Affero General Public License, version 3 only](LICENSE)
(`AGPL-3.0-only`). Retain existing copyright and third-party license notices.

## Releases and versioning

The version lives in `pyproject.toml` and `orthoplan/__init__.py` and is exposed
as `orthoplan.__version__` (it also stamps print/report artifacts). Policy: each
branch merged into `main` bumps the **minor** version (1.0.0 -> 1.1.0).
Maintainers tag releases as `vX.Y.0`. Contributors do not need to change the
version in a PR.

## Dependencies

New dependencies must be permissively licensed and recorded in
[docs/LICENSE_AUDIT.md](docs/LICENSE_AUDIT.md). Prefer the standard library;
heavy or optional dependencies go behind an extra in `pyproject.toml`.
