# Codex Notes

This repository is safety-boundary-first. Do not describe OpenSource Ortho as a medical device, Invisalign clone, clinical approval tool, autonomous treatment planner, complete treatment-planning system, or software that makes physical use safe. Preferred framing: clear-aligner planning safety playground and research toolkit.

When changing behavior, summarize it in your pull request description. When changing model-provider behavior, also update [docs/OpenAI_Agents.md](docs/OpenAI_Agents.md).

A core product goal is best-effort longitudinal tooth-motion simulation from existing scans.
Use and improve local segmentation and endpoint matching to infer intermediate weeks;
missing intermediate scans or unmet production segmentation thresholds alone must not
block a clearly labeled exploratory preview. Distinguish original observations from
estimated poses, expose weak/unmatched regions, and keep inferred motion separate
from reviewed treatment-plan data. See [docs/SCAN_HISTORY.md](docs/SCAN_HISTORY.md).

Model-generated findings are untrusted and must pass `lint_finding()` before display or export.

## Maintainability

Keep code composable and easy to review:

- prefer small modules with clear ownership boundaries
- keep files under the thresholds in [docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md)
- split code by responsibility, not by clever abstraction
- keep provider SDKs out of domain models
- keep UI rendering out of planning and evaluation logic
- run `python3 tools/check_maintainability.py` before commits that add or reorganize code

Codex hooks run the maintainability check before commit-status updates.

## Private development and public releases

Maintainer sequence: private feature branch → private `main` → filtered public
release branch based on public `main` → one public commit. Routine maintainer
pushes go to `john-lawniczak/OpenSourceOrtho-dev` (`private`). Public contributors
can use public forks and PRs. Never merge private ancestry into the public repo.
Use `tools/prepare_public_release.py` and [docs/PRIVATE_DEVELOPMENT.md](docs/PRIVATE_DEVELOPMENT.md).

Keep `TODO.md` on private branches; `public-release.json` excludes it from public
snapshots even though it is tracked. Dataset publication also requires individual
`consent.json` asset entries. `datasets/**/private/` remains excluded. USER_ONE week
18 scans and chipped-model metadata were explicitly approved for publication on
2026-11-12 and moved to `visits/progress-02/`; this does not authorize other private
contributions. Local painted labels stay local until separately incorporated.
