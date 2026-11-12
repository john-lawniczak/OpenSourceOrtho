"""Prepare one filtered public snapshot; never commit, push, or merge private ancestry."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from public_release_policy import git, release_paths


def prepare(repo, source, base, destination, branch):
    source = git(repo, "rev-parse", "--verify", f"{source}^{{commit}}").decode().strip()
    base = git(repo, "rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
    selected, excluded = release_paths(repo, source)
    if destination.exists():
        raise ValueError("Release destination must not exist")
    with tempfile.TemporaryDirectory(prefix="ortho-release-index-") as temp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index")}
        git(repo, "read-tree", source, env=env)
        if excluded:
            git(repo, "update-index", "--force-remove", "-z", "--stdin", env=env,
                data=b"\0".join(p.encode() for p in excluded) + b"\0")
        tree = git(repo, "write-tree", env=env).decode().strip()
    patch = git(repo, "diff", "--binary", "--full-index", base, tree)
    if not patch:
        raise ValueError("No public changes to release")
    # Reject formatting errors before creating a branch or a partial worktree.
    git(repo, "diff", "--check", base, tree)
    git(repo, "worktree", "add", "-b", branch, str(destination), base)
    git(repo, "config", f"branch.{branch}.pushRemote", "private")
    # The release index starts at the public base, not at the private source.
    git(destination, "apply", "--index", "--binary", "-", data=patch)
    git(destination, "diff", "--cached", "--check")
    record = {"source": source, "public_base": base, "snapshot_tree": tree,
              "branch": branch, "included_files": len(selected), "excluded_files": excluded}
    record_path = Path(git(destination, "rev-parse", "--absolute-git-dir").decode().strip()) / "release-review.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="private/main")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--branch")
    args = parser.parse_args()
    repo = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    if not args.worktree and not args.branch:
        source = git(repo, "rev-parse", "--verify", f"{args.source}^{{commit}}").decode().strip()
        selected, excluded = release_paths(repo, source)
        print(json.dumps({"source": source, "included_files": len(selected), "excluded_files": excluded}, indent=2))
        return
    if not args.worktree or not args.branch:
        parser.error("Use --worktree and --branch together, or neither for a read-only audit")
    record = prepare(repo, args.source, args.base, args.worktree.resolve(), args.branch)
    print(json.dumps(record, indent=2))
    print("Staged for review only. Validate this tree, then create one commit and explicitly publish.")


if __name__ == "__main__":
    main()
