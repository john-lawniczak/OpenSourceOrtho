#!/usr/bin/env bash
set -euo pipefail

if [[ "${OPEN_SOURCE_ORTHO_AMENDING:-}" == "1" ]]; then
  exit 0
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 "$ROOT/tools/update_dev_status.py"

if git -C "$ROOT" diff --quiet -- docs/Dev_history.md; then
  exit 0
fi

git -C "$ROOT" add docs/Dev_history.md
OPEN_SOURCE_ORTHO_AMENDING=1 git -C "$ROOT" commit --amend --no-edit
