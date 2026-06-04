from __future__ import annotations

import argparse
import sys

from orthoplan.evaluation.rules.movement_caps import evaluate_movement_caps
from orthoplan.io.serialization import plan_to_json, read_plan, write_plan
from orthoplan.io.stl_import import inspect_stl
from orthoplan.model.assets import MeshProvenance, bounding_box_sanity
from orthoplan.model.gaps import data_gaps
from orthoplan.model.plan import TreatmentPlan
from orthoplan.model.settings import TimelineSettings, TreatmentSettings
from orthoplan.planning.timeline import project_timeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orthoplan",
        description="OpenSource Ortho research toolkit CLI.",
    )
    parser.add_argument("--version", action="store_true", help="show package version")
    sub = parser.add_subparsers(dest="command")

    new_plan = sub.add_parser("new-plan", help="create a draft treatment plan")
    new_plan.add_argument("--id", required=True)
    new_plan.add_argument("--title", default="Untitled plan")
    new_plan.add_argument("--wear-interval", type=int, default=14, help="aligner wear days")
    new_plan.add_argument("--out", default=None, help="write plan JSON to this path")

    inspect = sub.add_parser("inspect-stl", help="show units-unverified STL metadata")
    inspect.add_argument("path")
    inspect.add_argument(
        "--provenance",
        choices=[p.value for p in MeshProvenance],
        default=MeshProvenance.PATIENT_DERIVED.value,
    )

    summary = sub.add_parser("plan-summary", help="summarize a serialized plan")
    summary.add_argument("path")
    return parser


def _cmd_new_plan(args: argparse.Namespace) -> int:
    plan = TreatmentPlan(
        id=args.id,
        title=args.title,
        settings=TreatmentSettings(timeline=TimelineSettings(wear_interval_days=args.wear_interval)),
    )
    if args.out:
        write_plan(plan, args.out)
        print(f"Wrote draft plan to {args.out}")
    else:
        print(plan_to_json(plan))
    return 0


def _cmd_inspect_stl(args: argparse.Namespace) -> int:
    try:
        asset = inspect_stl(args.path, provenance=MeshProvenance(args.provenance))
    except (OSError, ValueError) as exc:
        print(f"inspect-stl error: {exc}", file=sys.stderr)
        return 2
    print(asset.model_dump_json(indent=2))
    note = bounding_box_sanity(asset)
    print(f"\nScale note: {note}" if note else "\nScale note: none")
    return 0


def _cmd_plan_summary(args: argparse.Namespace) -> int:
    plan = read_plan(args.path)
    projection = project_timeline(plan)
    findings = evaluate_movement_caps(plan)
    print(f"Plan: {plan.title} ({plan.id})")
    print(f"Numbering: {plan.numbering_system}  Frame: {plan.coordinate_frame.name}")
    print(f"Stages: {len(plan.stages)}  Scans: {len(plan.scans)}")
    print(f"Scale confirmed: {plan.scale_confirmed}")
    print(
        f"Timeline projection: {projection.projected_duration_days} days "
        f"(~{projection.projected_duration_weeks} weeks) at "
        f"{projection.wear_interval_days}-day wear. {projection.caveat}"
    )
    print(f"Data gaps: {', '.join(data_gaps(plan)) or 'none declared'}")
    print(f"Movement-cap findings: {len(findings)}")
    for finding in findings:
        print(f"  - {finding.render().splitlines()[0]}")
    return 0


_COMMANDS = {
    "new-plan": _cmd_new_plan,
    "inspect-stl": _cmd_inspect_stl,
    "plan-summary": _cmd_plan_summary,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        from orthoplan import __version__

        print(__version__)
        return 0

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
