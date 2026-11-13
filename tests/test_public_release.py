"""Exercise publication filtering and repeated releases in disposable Git histories."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/prepare_public_release.py"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def write(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit(repo, message):
    git(repo, "add", ".")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path):
    repo = tmp_path / "private"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Release test")
    git(repo, "config", "user.email", "release@example.invalid")
    git(repo, "config", "core.hooksPath", "/dev/null")
    git(repo, "config", "commit.gpgsign", "false")
    write(repo, "app.txt", "old")
    base = commit(repo, "Public base")
    write(repo, "public-release.json", (ROOT / "public-release.json").read_text())
    write(repo, "TODO.md", "private notes")
    write(repo, "nested/todo.md", "also private")
    write(repo, ".env", "synthetic secret")
    write(repo, "app.txt", "new")
    case = "datasets/spec-test/"
    consent = {"consent_acknowledged": True, "phi_removed": True,
               "public_assets": ["consent.json", "visits/progress-02/scan.stl"]}
    write(repo, case + "consent.json", json.dumps(consent))
    write(repo, case + "visits/progress-02/scan.stl", "approved geometry")
    write(repo, case + "visits/progress-02/unapproved.txt", "unapproved")
    write(repo, case + "private/new-visit/scan.stl", "private geometry")
    source = commit(repo, "Private feature")
    # Ignored/untracked files must not leak into the prepared tree either.
    write(repo, "local-session.txt", "local only")
    return repo, base, source


def prepare(repo, source, base, destination, branch):
    return subprocess.run([sys.executable, str(TOOL), "--source", source, "--base", base,
                           "--worktree", str(destination), "--branch", branch], cwd=repo,
                          capture_output=True, text=True)


def test_snapshot_filters_tracked_notes_and_unapproved_data_and_keeps_one_parent(history, tmp_path):
    repo, base, source = history
    destination = tmp_path / "release"
    result = prepare(repo, source, base, destination, "release/first")
    assert result.returncode == 0, result.stderr
    files = git(destination, "ls-files").splitlines()
    assert "datasets/spec-test/visits/progress-02/scan.stl" in files
    assert not any("todo" in p.lower() or "private/" in p or "unapproved" in p for p in files)
    assert ".env" not in files and "local-session.txt" not in files
    assert git(destination, "rev-parse", "HEAD") == base  # No implicit commit.
    git(destination, "commit", "-qm", "Public release")
    release = git(destination, "rev-parse", "HEAD")
    assert git(destination, "rev-list", "--parents", "-n", "1", "HEAD").split() == [release, base]
    assert git(repo, "rev-parse", "HEAD") == source
    assert git(repo, "config", "branch.release/first.pushRemote") == "private"
    # A subsequent private batch has no public release commit in its ancestry.
    (repo / "app.txt").unlink()
    next_source = commit(repo, "Remove old app")
    second = tmp_path / "second"
    result = prepare(repo, next_source, release, second, "release/second")
    assert result.returncode == 0, result.stderr
    assert not (second / "app.txt").exists()
    git(second, "commit", "-qm", "Next release")
    assert git(second, "rev-parse", "HEAD^") == release
    assert git(second, "rev-list", "--count", f"{release}..HEAD") == "1"


def test_missing_approved_asset_fails_before_creating_release(history, tmp_path):
    repo, base, _ = history
    (repo / "datasets/spec-test/visits/progress-02/scan.stl").unlink()
    source = commit(repo, "Broken scope")
    destination = tmp_path / "release"
    result = prepare(repo, source, base, destination, "release/broken")
    assert result.returncode != 0 and "Missing approved asset" in result.stderr
    assert not destination.exists()


@pytest.mark.parametrize("contents,diagnostic", [
    ("trailing spaces  \n", "app.txt:1: trailing whitespace"),
    ("valid line\n\n", "app.txt:2: new blank line at EOF"),
])
def test_whitespace_failure_leaves_no_release_branch_or_worktree(history, tmp_path, contents, diagnostic):
    repo, base, _ = history
    write(repo, "app.txt", contents)
    source = commit(repo, "Formatting error")
    destination = tmp_path / "release"
    result = prepare(repo, source, base, destination, "release/formatting")
    assert result.returncode != 0
    assert diagnostic in result.stderr
    assert "Traceback" not in result.stderr
    assert not destination.exists()
    assert git(repo, "branch", "--list", "release/formatting") == ""


def test_unapproved_symlink_cannot_enter_release(history, tmp_path):
    repo, base, _ = history
    (repo / "linked-secret").symlink_to(".env")
    source = commit(repo, "Accidental symlink")
    result = prepare(repo, source, base, tmp_path / "release", "release/symlink")
    assert result.returncode != 0 and "regular tracked files" in result.stderr
