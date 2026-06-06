from __future__ import annotations

import argparse
import os
import sys

from orthoplan.evaluation.acquisition import acquisition_advice
from orthoplan.evaluation.engine import run_rules
from orthoplan.cli_contribution import add_contribution_parser, cmd_register_contribution
from orthoplan.cli_mesh import add_mesh_parsers, cmd_inspect_stl, cmd_register_mesh
from orthoplan.cli_packages import (
    add_measurement_lab_parser,
    add_print_package_parser,
    cmd_measurement_lab,
    cmd_print_package,
)
from orthoplan.io.serialization import plan_to_json, read_plan, write_plan
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

    add_mesh_parsers(sub)
    add_contribution_parser(sub)

    summary = sub.add_parser("plan-summary", help="summarize a serialized plan")
    summary.add_argument("path")

    serve = sub.add_parser("serve", help="run the local UI dev server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    advise = sub.add_parser("advise", help="run the optional model advisory layer over a plan")
    advise.add_argument("path")
    advise.add_argument("--provider", choices=["openai", "claude-code"], default="openai")
    advise.add_argument("--model", default=None, help="override the provider's default model")

    report = sub.add_parser("report", help="generate a reproducible handoff report")
    report.add_argument("path")
    report.add_argument("--out", default=None, help="write report JSON to this path")
    report.add_argument("--reviewer", default=None, help="reviewer name/id to include in report")
    report.add_argument(
        "--signing-key-env",
        default=None,
        help="environment variable containing an HMAC signing key",
    )

    acquisition = sub.add_parser("acquisition", help="rank missing data by deterministic impact")
    acquisition.add_argument("path")
    acquisition.add_argument("--json", action="store_true", help="emit acquisition advice as JSON")

    add_print_package_parser(sub)
    add_measurement_lab_parser(sub)
    return parser


def _cmd_new_plan(args: argparse.Namespace) -> int:
    plan = TreatmentPlan(
        id=args.id,
        title=args.title,
        settings=TreatmentSettings(
            timeline=TimelineSettings(wear_interval_days=args.wear_interval)
        ),
    )
    if args.out:
        write_plan(plan, args.out)
        print(f"Wrote draft plan to {args.out}")
    else:
        print(plan_to_json(plan))
    return 0


def _cmd_plan_summary(args: argparse.Namespace) -> int:
    try:
        plan = read_plan(args.path)
    except (OSError, ValueError) as exc:
        print(f"plan-summary error: {exc}", file=sys.stderr)
        return 2
    projection = project_timeline(plan)
    findings = run_rules(plan)
    advice = acquisition_advice(plan)
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
    print(f"Acquisition advice: {len(advice.impacts)} applicable item(s)")
    print(f"Findings: {len(findings)}")
    for finding in findings:
        print(f"  - {finding.render().splitlines()[0]}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from orthoplan.server import serve

    serve(host=args.host, port=args.port)
    return 0


def _build_provider(name: str, model: str | None):
    if name == "openai":
        from orthoplan.evaluation.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(model=model) if model else OpenAIProvider()
    from orthoplan.evaluation.providers.claude_code_provider import ClaudeCodeProvider

    return ClaudeCodeProvider(model=model) if model else ClaudeCodeProvider()


def _cmd_advise(args: argparse.Namespace) -> int:
    from orthoplan.evaluation.advisory import request_advisory

    try:
        plan = read_plan(args.path)
        provider = _build_provider(args.provider, args.model)
        result = request_advisory(plan, provider)
    except (RuntimeError, OSError) as exc:
        print(f"advise error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"advise error: {exc}", file=sys.stderr)
        return 2

    if result.parse_error:
        print(f"Advisory rejected (unparseable): {result.parse_error}")
    print(f"Accepted advisory findings: {len(result.accepted)} (provider={result.provider})")
    for finding in result.accepted:
        print(f"  {finding.render().splitlines()[0]}")
    print(f"Rejected by lint: {len(result.rejected)}")
    for rejection in result.rejected:
        print(f"  - {rejection.reason}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from orthoplan.reporting import build_handoff_report, report_to_json

    try:
        plan = read_plan(args.path)
    except (OSError, ValueError) as exc:
        print(f"report error: {exc}", file=sys.stderr)
        return 2

    signing_key = os.environ.get(args.signing_key_env) if args.signing_key_env else None
    body = report_to_json(
        build_handoff_report(plan, reviewer=args.reviewer, signing_key=signing_key)
    )
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(body + "\n", encoding="utf-8")
        print(f"Wrote handoff report to {args.out}")
    else:
        print(body)
    return 0


def _cmd_acquisition(args: argparse.Namespace) -> int:
    from orthoplan.evaluation.acquisition import acquisition_advice

    try:
        plan = read_plan(args.path)
    except (OSError, ValueError) as exc:
        print(f"acquisition error: {exc}", file=sys.stderr)
        return 2

    advice = acquisition_advice(plan)
    if args.json:
        print(advice.model_dump_json(indent=2))
        return 0
    print(f"Acquisition advisor for: {plan.title} ({plan.id})")
    print(
        f"Baseline: {advice.baseline_finding_count} finding(s), "
        f"{len(advice.baseline_data_gaps)} data gap(s)."
    )
    print(advice.caveat)
    if not advice.impacts:
        print("No missing data modalities are currently applicable.")
        return 0
    for index, impact in enumerate(advice.impacts, start=1):
        print(f"\n{index}. {impact.label} [{impact.modality}] score {impact.priority_score:.1f}")
        print(f"   Acquire: {impact.acquisition}")
        if impact.closes_data_gaps:
            print(f"   Closes gaps: {', '.join(impact.closes_data_gaps)}")
        if impact.resolves:
            print("   Would clear absence-of-data finding(s):")
            for finding in impact.resolves:
                print(f"     - {finding.severity.upper()}: {finding.title}")
        if impact.surfaces:
            print("   Would unlock currently-suppressed check(s):")
            for finding in impact.surfaces:
                print(f"     - {finding.severity.upper()}: {finding.title}")
        print(f"   Note: {impact.note}")
    return 0


_COMMANDS = {
    "new-plan": _cmd_new_plan,
    "inspect-stl": cmd_inspect_stl,
    "register-mesh": cmd_register_mesh,
    "register-contribution": cmd_register_contribution,
    "plan-summary": _cmd_plan_summary,
    "serve": _cmd_serve,
    "advise": _cmd_advise,
    "report": _cmd_report,
    "acquisition": _cmd_acquisition,
    "print-package": cmd_print_package,
    "measurement-lab": cmd_measurement_lab,
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
