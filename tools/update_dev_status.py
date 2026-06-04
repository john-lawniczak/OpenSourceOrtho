from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEV_HISTORY = ROOT / "docs" / "Dev_history.md"


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable"


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    commit = git_value("rev-parse", "--short", "HEAD")
    subject = git_value("log", "-1", "--pretty=%s")

    entry = (
        f"\n### {now} - Commit {commit}\n\n"
        f"- Commit subject: {subject}\n"
        "- Status: development history hook observed a commit from Claude Code.\n"
    )

    with DEV_HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(entry)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
