#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
python3 "$PROJECT_DIR/tools/check_maintainability.py"

