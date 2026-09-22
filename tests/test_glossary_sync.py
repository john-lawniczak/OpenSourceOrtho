from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_shared_glossary_generated_targets_are_current() -> None:
    result = subprocess.run(
        [sys.executable, "tools/sync_glossary.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
