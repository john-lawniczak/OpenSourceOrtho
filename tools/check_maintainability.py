#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [ROOT / "orthoplan", ROOT / "tests", ROOT / "tools"]
FIRST_PARTY_SOURCE_DIRS = [ROOT / "ui", ROOT / "mobile" / "ios", ROOT / "mobile" / "android"]
BASELINE_PATH = ROOT / "tools" / "maintainability_baseline.json"
WARN_FILE_LINES = 300
STRICT_FILE_LINES = 500
WARN_FUNCTION_LINES = 60
WARN_CLASS_LINES = 150


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str
    strict: bool = False


def python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        if directory.exists():
            files.extend(sorted(directory.rglob("*.py")))
    return files


def first_party_source_files() -> list[Path]:
    extensions = {".js", ".swift", ".kt"}
    ignored_parts = {"vendor", ".build", "build", ".gradle", ".derivedData"}
    files: list[Path] = []
    for directory in FIRST_PARTY_SOURCE_DIRS:
        if not directory.exists():
            continue
        files.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and path.suffix in extensions
            and not ignored_parts.intersection(path.parts)
            and not path.name.endswith(".test.js")
        )
    return sorted(files)


def load_line_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {str(path): int(limit) for path, limit in payload.get("line_budgets", {}).items()}


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def node_lines(node: ast.AST) -> int:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def check_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    relative = path.relative_to(ROOT)
    lines = line_count(path)

    if lines > STRICT_FILE_LINES:
        findings.append(
            Finding(
                path=relative,
                message=f"{lines} lines exceeds split-required threshold of {STRICT_FILE_LINES}",
                strict=True,
            )
        )
    elif lines > WARN_FILE_LINES:
        findings.append(
            Finding(
                path=relative,
                message=f"{lines} lines exceeds warning threshold of {WARN_FILE_LINES}",
            )
        )

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count = node_lines(node)
            if count > WARN_FUNCTION_LINES:
                findings.append(
                    Finding(
                        path=relative,
                        message=(
                            f"function {node.name!r} is {count} lines; "
                            f"target is {WARN_FUNCTION_LINES}"
                        ),
                    )
                )
        elif isinstance(node, ast.ClassDef):
            count = node_lines(node)
            if count > WARN_CLASS_LINES:
                findings.append(
                    Finding(
                        path=relative,
                        message=f"class {node.name!r} is {count} lines; target is {WARN_CLASS_LINES}",
                    )
                )

    return findings


def source_line_findings(relative: Path, lines: int, baseline: dict[str, int]) -> list[Finding]:
    relative_name = relative.as_posix()
    legacy_limit = baseline.get(relative_name)
    if legacy_limit is not None:
        if lines > legacy_limit:
            return [Finding(relative, f"{lines} lines exceeds legacy budget of {legacy_limit}", strict=True)]
        return []
    if lines > STRICT_FILE_LINES:
        return [
            Finding(
                relative,
                f"{lines} lines exceeds split-required threshold of {STRICT_FILE_LINES}",
                strict=True,
            )
        ]
    if lines > WARN_FILE_LINES:
        return [Finding(relative, f"{lines} lines exceeds warning threshold of {WARN_FILE_LINES}")]
    return []


def check_source_file(path: Path, baseline: dict[str, int]) -> list[Finding]:
    relative = path.relative_to(ROOT)
    return source_line_findings(relative, line_count(path), baseline)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenSource Ortho maintainability guardrails.")
    parser.add_argument("--strict", action="store_true", help="fail on warning-level findings")
    args = parser.parse_args()

    findings: list[Finding] = []
    for path in python_files():
        findings.extend(check_file(path))
    baseline = load_line_baseline()
    for path in first_party_source_files():
        findings.extend(check_source_file(path, baseline))

    if not findings:
        print("Maintainability check passed.")
        return 0

    print("Maintainability findings:")
    for finding in findings:
        level = "ERROR" if finding.strict else "WARN"
        print(f"- {level} {finding.path}: {finding.message}")

    if args.strict or any(finding.strict for finding in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
