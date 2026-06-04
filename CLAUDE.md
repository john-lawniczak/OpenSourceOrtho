# Claude Code Notes

This repository is safety-boundary-first. Do not describe OpenSource Ortho as a medical device, Invisalign clone, clinical approval tool, or autonomous treatment planner.

When changing behavior, update [Dev_history.md](Dev_history.md). When changing model-provider behavior, also update [OpenAI_Agents.md](OpenAI_Agents.md).

Model-generated findings are untrusted and must pass `lint_finding()` before display or export.

## Maintainability

Keep code composable and easy to review:

- prefer small modules with clear ownership boundaries
- keep files under the thresholds in [MAINTAINABILITY.md](MAINTAINABILITY.md)
- split code by responsibility, not by clever abstraction
- keep provider SDKs out of domain models
- keep UI rendering out of planning and evaluation logic
- run `python3 tools/check_maintainability.py` before commits that add or reorganize code

Claude hooks run the maintainability check before commit-status updates.
