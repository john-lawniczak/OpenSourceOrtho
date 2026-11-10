# Codex Notes

This repository is safety-boundary-first. Do not describe OpenSource Ortho as a medical device, Invisalign clone, clinical approval tool, autonomous treatment planner, complete treatment-planning system, or software that makes physical use safe. Preferred framing: clear-aligner planning safety playground and research toolkit.

When changing behavior, summarize it in your pull request description. When changing model-provider behavior, also update [docs/OpenAI_Agents.md](docs/OpenAI_Agents.md).

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

Develop and push to the private `john-lawniczak/OpenSourceOrtho-dev` repository
(`private` remote). The public `origin` is for fetching released work and explicit
releases only. Publish reviewed changes as one new commit based on public `main`,
without merging private development history. Follow
[docs/PRIVATE_DEVELOPMENT.md](docs/PRIVATE_DEVELOPMENT.md).

`datasets/**/private/` contains private contributions. Exclude it from public
release trees and dataset asset allowlists unless publication is explicitly
authorized. Private contribution permission does not grant public redistribution.
