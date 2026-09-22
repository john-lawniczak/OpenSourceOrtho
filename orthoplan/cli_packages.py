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


def add_segmentation_benchmark_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "segmentation-benchmark",
        help="score local segmentation against a labelled real-scan manifest",
    )
    parser.add_argument("--manifest", required=True, help="labelled real-scan corpus manifest")
    parser.add_argument("--json", action="store_true", help="emit benchmark report as JSON")
    parser.add_argument(
        "--min-triangle-label-accuracy",
        type=float,
        default=0.95,
        help="minimum labelled triangle accuracy for each scored case",
    )
    parser.add_argument(
        "--min-region-purity",
        type=float,
        default=0.95,
        help="minimum per-region purity for each scored case",
    )
    parser.add_argument(
        "--min-cases",
        type=int,
        default=1,
        help="minimum license-clear labelled cases required for a passing report",
    )


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


def cmd_segmentation_benchmark(args: argparse.Namespace) -> int:
    from orthoplan.validation.segmentation_real_report import labelled_real_scan_report

    try:
        report = labelled_real_scan_report(
            manifest_path=args.manifest,
            min_triangle_label_accuracy=args.min_triangle_label_accuracy,
            min_region_purity=args.min_region_purity,
            min_cases=args.min_cases,
        )
    except (OSError, ValueError) as exc:
        print(f"segmentation-benchmark error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(report.model_dump_json(indent=2))
        return 0 if report.passed else 1

    status = "PASS" if report.passed else "FAIL"
    print(f"{status} labelled segmentation benchmark")
    print(f"Candidate: {report.candidate_backend}  Fallback: {report.fallback_backend}")
    print(f"Scored cases: {report.scored_case_count} / minimum {report.min_cases}")
    print(report.caveat)
    for case in report.cases:
        case_status = "PASS" if case.passed else "SKIP" if case.skipped_reason else "FAIL"
        print(f"\n{case_status} {case.case_id}")
        if case.skipped_reason:
            print(f"  skipped: {case.skipped_reason}")
            continue
        print(
            "  accuracy="
            f"{case.triangle_label_accuracy:.3f} purity={case.region_purity:.3f} "
            f"teeth={case.observed_tooth_count}/{case.expected_tooth_count}"
        )
        print(
            "  fallback="
            f"{case.fallback_triangle_label_accuracy:.3f}/"
            f"{case.fallback_region_purity:.3f} "
            f"review_burden_delta={case.review_burden_delta_vs_fallback:.3f}"
        )
        for failure in case.failures:
            print(f"  - {failure}")
    return 0 if report.passed else 1
