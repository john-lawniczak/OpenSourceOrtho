from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from orthoplan.io.serialization import read_plan


def add_print_package_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("print-package", help="generate printable stage proxy files")
    parser.add_argument("path")
    parser.add_argument("--out", required=True, help="directory for generated files")
    parser.add_argument("--zip", action="store_true", help="also write a zip package")
    parser.add_argument(
        "--email-draft",
        action="store_true",
        help="also write an .eml draft",
    )


def add_measurement_lab_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("measurement-lab", help="run measurement truth cases")
    parser.add_argument("--case", default=None, help="run one measurement truth case")
    parser.add_argument("--json", action="store_true", help="emit lab results as JSON")


def add_validation_benchmark_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "validation-benchmark",
        help="emit tracked geometry, corpus, and longitudinal data benchmark metrics",
    )
    parser.add_argument("--json", action="store_true", help="emit benchmark report as JSON")


def cmd_print_package(args: argparse.Namespace) -> int:
    from orthoplan.printing import export_print_package

    try:
        plan = read_plan(args.path)
    except (OSError, ValueError) as exc:
        print(f"print-package error: {exc}", file=sys.stderr)
        return 2

    result = export_print_package(
        plan,
        args.out,
        make_zip=args.zip,
        make_email_draft=args.email_draft,
    )
    print(f"Wrote print package manifest: {result.manifest_path}")
    for path in result.artifact_paths:
        print(f"Wrote printable file: {path}")
    if result.zip_path:
        print(f"Wrote zip package: {result.zip_path}")
    if result.email_draft_path:
        print(f"Wrote email draft: {result.email_draft_path}")
    print(result.caveat)
    return 0


def cmd_measurement_lab(args: argparse.Namespace) -> int:
    from orthoplan.validation import run_measurement_lab

    try:
        results = run_measurement_lab(args.case)
    except KeyError as exc:
        print(f"measurement-lab error: unknown case {exc.args[0]!r}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([result.model_dump() for result in results], indent=2, sort_keys=True))
    else:
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} {result.case_id}")
            for failure in result.failures:
                print(f"  - {failure}")
    return 0 if all(result.passed for result in results) else 1


def cmd_validation_benchmark(args: argparse.Namespace) -> int:
    from orthoplan.validation import run_validation_benchmarks

    report = run_validation_benchmarks()
    if args.json:
        print(report.model_dump_json(indent=2))
        return 0
    print(report.benchmark_id)
    print(report.caveat)
    for component, metrics in report.by_component().items():
        print(f"\n{component}")
        for metric in metrics:
            unit = f" {metric.unit}" if metric.unit else ""
            print(f"  - {metric.name}: {metric.value}{unit} ({metric.case_id})")
    return 0
