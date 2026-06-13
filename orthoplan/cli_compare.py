from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.io.serialization import read_plan


def add_compare_parser(subparsers: Any) -> None:
    compare = subparsers.add_parser("compare-setups", help="compare two setup plan snapshots")
    compare.add_argument("before")
    compare.add_argument("after")
    compare.add_argument(
        "--live-restage",
        action="store_true",
        help="restage the second plan before comparing it to the first",
    )
    compare.add_argument("--json", action="store_true", help="emit comparison as JSON")


def cmd_compare_setups(args: argparse.Namespace) -> int:
    from orthoplan.setup_compare import compare_setups, live_restage_comparison

    try:
        before = read_plan(args.before)
        after = read_plan(args.after)
    except (OSError, ValueError) as exc:
        print(f"compare-setups error: {exc}", file=sys.stderr)
        return 2

    result = (
        live_restage_comparison(before, after)
        if args.live_restage
        else compare_setups(before, after)
    )
    if args.json:
        print(result.model_dump_json(indent=2))
        return 0
    comparison = result.comparison if args.live_restage else result
    print(f"Setup comparison: {comparison.before_id} -> {comparison.after_id}")
    print(f"Stages: {comparison.before_stage_count} -> {comparison.after_stage_count}")
    print(f"Changed teeth: {len(comparison.changed_teeth)}")
    for diff in comparison.changed_teeth:
        axes = ", ".join(f"{axis} {value:+g}" for axis, value in diff.delta.items())
        print(f"  - {diff.tooth}: {axes}")
    if args.live_restage:
        print(f"Live restage source: {result.source}")
        print(
            f"Timeline days: {result.before_timeline_days} "
            f"-> {result.restaged_timeline_days}"
        )
    print(comparison.caveat)
    return 0
