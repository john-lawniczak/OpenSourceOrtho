from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [ROOT / "orthoplan", ROOT / "tests", ROOT / "tools"]
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenSource Ortho maintainability guardrails.")
    parser.add_argument("--strict", action="store_true", help="fail on warning-level findings")
    args = parser.parse_args()

    findings: list[Finding] = []
    for path in python_files():
        findings.extend(check_file(path))

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

