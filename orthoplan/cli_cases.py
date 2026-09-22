"""CLI for plan version history (the case store).

Thin wrappers over ``case_api.py`` so saving/listing plan versions works from the
terminal as well as the UI. Grouped out of ``cli.py`` to keep the dispatcher small.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.case_api import (
    case_versions_payload,
    list_cases_payload,
    save_plan_version_payload,
)
from orthoplan.cases import default_case_store
from orthoplan.io.serialization import read_plan


def add_case_parsers(sub: Any) -> None:
    save = sub.add_parser("case-save", help="save a plan as a new version in the case store")
    save.add_argument("path")
    save.add_argument("--store", default=None, help="case store JSON path")
    save.add_argument("--case-id", default=None, help="case id (defaults to plan id)")
    save.add_argument("--note", default=None, help="version note")

    listing = sub.add_parser("case-list", help="list cases in the case store")
    listing.add_argument("--store", default=None, help="case store JSON path")

    versions = sub.add_parser("case-versions", help="list versions of a case")
    versions.add_argument("case_id")
    versions.add_argument("--store", default=None, help="case store JSON path")


def _store(args: argparse.Namespace) -> str:
    return args.store or str(default_case_store())


def cmd_case_save(args: argparse.Namespace) -> int:
    try:
        plan = read_plan(args.path)
    except (OSError, ValueError) as exc:
        print(f"case-save error: {exc}", file=sys.stderr)
        return 2
    result = save_plan_version_payload(
        {"plan": plan.model_dump(mode="json"), "case_id": args.case_id, "note": args.note},
        store_path=_store(args),
    )
    if not result["ok"]:
        print(f"case-save error: {'; '.join(result['errors'])}", file=sys.stderr)
        return 2
    print(
        f"Saved {result['version']['version_id']} to case {result['case_id']} "
        f"({len(result['versions'])} version(s))"
    )
    return 0


def cmd_case_list(args: argparse.Namespace) -> int:
    result = list_cases_payload(store_path=_store(args))
    if not result["cases"]:
        print("No cases in the store.")
        return 0
    for case in result["cases"]:
        print(f"{case['case_id']}  {case['version_count']} version(s)  {case['title']}")
    return 0


def cmd_case_versions(args: argparse.Namespace) -> int:
    result = case_versions_payload(args.case_id, store_path=_store(args))
    if not result["ok"]:
        print(f"case-versions error: {'; '.join(result['errors'])}", file=sys.stderr)
        return 2
    for v in result["versions"]:
        print(f"{v['version_id']}  {v['plan_hash'][:12]}  {v['created_at']}  {v['note'] or ''}")
    return 0
