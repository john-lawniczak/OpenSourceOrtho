# Private development and public releases

## Maintainer workflow

**Private feature branch → private main → reviewed public snapshot → one public commit.**

The maintainer integrates work in `john-lawniczak/OpenSourceOrtho-dev` (`private`).
Public releases go to `john-lawniczak/OpenSourceOrtho` (`origin`). These are separate
histories: never merge private main into public main or push private main to origin.
Public contributors can fork the public repository and open PRs; private access
is not required.

Keep `TODO.md` tracked on private branches. It is deliberately excluded from every
public snapshot by `public-release.json`. `.gitignore` alone does not exclude a
tracked file. Local case stores, painted labels, secrets, and development logs also
stay out. The public roadmap belongs in `docs/TOOL_IMPROVEMENT_PHASES.md`.

## 1. Develop and integrate privately

Configure each checkout once:

```bash
git config remote.pushDefault private
git config push.default current
git fetch private
git switch -c work/my-change private/main
git push -u private HEAD
```

After implementation, review and tests, merge the feature PR into **private main**.
Preserve its existing history. If branches have diverged, use an integration branch
and resolve conflicts explicitly; do not reset main or blanket-select one side.
Fetch the resulting private main before preparing a release.

The November 12 integration of private main (`a7ff308`) into
`data/user-one-week-18` resolved 50 conflicting paths. For 38 paths, private main's
content exactly matched the earlier public snapshot (`a9d4654`), already an
ancestor of the feature branch; the newer feature versions were retained. The
remaining resolutions preserve the current private roadmap, publication records,
explicit dataset inventory, baseline annotations and week 18 scans. The omitted
reference video stays omitted. No scan geometry was regenerated for this merge.
Merge the reviewed feature PR into private main before using it as a release
source. The release tool accepts an explicit `--source` for a reviewed exception;
its default is `private/main`.

## 2. Review publication scope

Only committed source files are considered. `public-release.json` excludes private
notes and local records even if accidentally tracked. Dataset files inside a
`spec-*` case must also appear explicitly in that case's committed `consent.json`
`public_assets`. Never approve an entire private directory with a wildcard.

The contributor authorized publication on **2026-11-12** of USER_ONE's reported
week 18 original upper/lower scans, both Fusion H4/H6 lower captures, and their
chipped-model metadata and evaluations. These unchanged scans now live under
`datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/` and are individually
allowlisted. The historical private sharing records remain as provenance.
`datasets/**/private/` continues to mean unpublished contributions. This specific
authorization does not confer third-party reference video rights or cover application
credentials. The contributor subsequently authorized all USER_ONE contributed case
data for publication, including wisdom-tooth removal history and the inventoried
upper baseline annotations. Keep each published asset explicit in `consent.json`;
local editing sessions remain outside release trees until incorporated into that inventory.

## 3. Prepare a public release worktree

```bash
git fetch private
git fetch origin
python3 tools/prepare_public_release.py --source private/main
python3 tools/prepare_public_release.py --source private/main --base origin/main \
  --branch release/2026-11-12 --worktree ../OpenSourceOrtho-public-release
```

Use a fresh branch name and nonexistent destination each time. The first command
only audits exclusions. The second stages a filtered snapshot in a separate
worktree based on the exact public tip. It never commits, merges or pushes.
A private-source SHA, public-base SHA, snapshot tree hash and exclusion inventory
are recorded in that worktree's Git metadata as `release-review.json` (not public).
The source branch and its working tree are left untouched. Uncommitted changes are
not exported; commit intended changes privately first.

The snapshot represents the selected source tree, including deletions. Review
upstream public changes and integrate them privately before export so a later
snapshot does not undo community contributions. Do not merge the previous private
release history into public main. Avoid the obsolete local `publish_snapshot.sh`:
it created a new repository and exported every tracked file.

## 4. Validate the exact staged release

Inside the release worktree, install the relevant project extras and run:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
python3 tools/build_dataset_catalog.py --check
python3 tools/check_maintainability.py --strict
ruff check .
pytest -q
node --test
pytest tests/e2e -q
```

Run the full CI dependency matrix, including mesh-processing, motion-preview,
learned segmentation and volume-review extras. Review the complete diff, dataset
scope, binary sizes and credentials, not just the test results. Fix browser failures
before release. Keep fixes in private development and regenerate the snapshot when
possible. Include behavior changes and validation in release notes/PR description;
update `docs/OpenAI_Agents.md` for provider behavior changes.

## 5. Commit and publish once

```bash
git commit -m "Release scan review and longitudinal research improvements"
git rev-list --count origin/main..HEAD
git rev-list --parents -n 1 HEAD
```

The count must be **1**, and the sole parent must equal the recorded public-base
SHA. Check the committed file list again: no TODO, private data or local stores.
Fetch origin once more. If public main advanced, reconcile those changes privately
and rebuild on its new tip; never force-push public main.

After the concrete release diff is approved for publication:

```bash
git push origin HEAD:refs/heads/release/2026-11-12
```

Open a PR into public main and **squash merge** it after CI succeeds. Public main
gains exactly one commit; a normal merge adds an extra merge commit. Record the
public release SHA and private source SHA in the private release/PR record. Retain
private history, and use the same sequence for the next batch. Routine pushes
continue to go to private; publishing always names origin explicitly.
