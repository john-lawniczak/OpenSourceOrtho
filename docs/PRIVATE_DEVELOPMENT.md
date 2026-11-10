# Private development and public releases

Routine development belongs in `john-lawniczak/OpenSourceOrtho-dev`, which is
private. The public repository is `john-lawniczak/OpenSourceOrtho`.

## Local setup

Use `private` for the development remote and `origin` for the public remote.
Verify visibility before pushing personal contributions:

```bash
gh repo view john-lawniczak/OpenSourceOrtho-dev --json nameWithOwner,isPrivate
git config remote.pushDefault private
git config push.default current
```

For a new development branch, fetch public `main` and branch from it, or continue
an existing private branch that already contains the work you need. Fetch and
inspect remote changes before merging. Preserve any existing private history.

```bash
git fetch origin
git switch -c work/my-change origin/main
git config branch.work/my-change.pushRemote private
# Make and validate the changes, then commit.
git push -u private HEAD
```

After setting the upstream, ordinary `git push` goes to the private repository.
These settings are local to each checkout; repeat setup in a new clone. Explicit
pushes to `origin`, `backup`, or `gitlab` bypass the private default, so reserve
those for an authorized release. Use authenticated HTTPS if SSH is unavailable.

This checkout's local post-merge hook may create a version-bump commit when a
fast-forward lands on a merge commit. For a sync that must exactly match upstream,
use `OPEN_SOURCE_ORTHO_BUMPING=1 git merge --ff-only origin/main` and verify the tip.

## Private case contributions

Store private visit bundles at `datasets/<existing-specimen-id>/private/<visit>/`.
Keep the same specimen ID and pseudonym. Each bundle has a supplementary manifest,
source metadata, and unchanged scan bytes. Its manifest covers only that visit;
the case-root manifest remains the published subset.

Do not add private files to the case's `consent.json` public asset allowlist or
public catalog. A private bundle's consent acknowledgement covers its documented
private contribution scope only. The HTTP dataset resolver does not serve assets
outside the case-root allowlist. Git privacy still depends on pushing to the
private repository and excluding these files from release trees.

## Publish one clean commit when ready

1. Fetch public `origin/main` and create a separate release worktree/branch from
   that exact tip. Record the selected private development commit.
2. Transfer only reviewed, publication-approved changes into the release tree.
   Exclude `datasets/**/private/`, ignored local records, credentials, and assets
   outside the documented publication scope. Do not merge the private branch or
   copy its entire tree without filtering. Squashing alone does not remove data.
3. Review the complete staged diff and file list. Run the relevant tests,
   `python3 tools/build_dataset_catalog.py --check`,
   `python3 tools/check_maintainability.py --strict`, and `git diff --cached --check`.
4. Create one commit whose sole parent is the fetched public `main`. Confirm
   that it contains no private records or private development ancestry.
5. With explicit authorization to publish, push that release commit to the
   public repository. If public `main` advanced, rebuild on its new tip;
   do not force-push public history.

The week 18 contribution is private-only. A future public release needs an
explicit scope decision before including its scans or metadata. This workflow
does not change any previously published case permissions.
