"""CLI for scan inspection and local mesh-workspace registration.

Grouped out of ``cli.py`` so the mesh commands own a small module, keeping the
top-level dispatcher focused and within the maintainability size guardrails.
Every supported scan format is accepted; ``inspect-stl`` remains as an alias of
``inspect-scan`` for existing scripts.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.io.mesh_import import SUPPORTED_FORMATS_TEXT, inspect_mesh
from orthoplan.mesh_workspace import register_scan_mesh
from orthoplan.model.assets import MeshProvenance, bounding_box_sanity


def add_mesh_parsers(sub: Any) -> None:
    for name in ("inspect-scan", "inspect-stl"):
        inspect = sub.add_parser(
            name, help=f"show units-unverified scan metadata ({SUPPORTED_FORMATS_TEXT})"
        )
        inspect.add_argument("path")
        inspect.add_argument(
            "--provenance",
            choices=[p.value for p in MeshProvenance],
            default=MeshProvenance.PATIENT_DERIVED.value,
        )

    register = sub.add_parser(
        "register-mesh", help=f"import a scan into the local mesh workspace ({SUPPORTED_FORMATS_TEXT})"
    )
    register.add_argument("path")
    register.add_argument("--workspace", default=None, help="mesh workspace directory")
    register.add_argument(
        "--provenance",
        choices=[p.value for p in MeshProvenance],
        default=MeshProvenance.IMPORTED.value,
    )


def cmd_inspect_scan(args: argparse.Namespace) -> int:
    # Echo whichever alias the user typed (``inspect-scan`` or ``inspect-stl``).
    command = getattr(args, "command", "inspect-scan")
    try:
        asset = inspect_mesh(args.path, provenance=MeshProvenance(args.provenance))
    except (OSError, ValueError) as exc:
        print(f"{command} error: {exc}", file=sys.stderr)
        return 2
    print(asset.model_dump_json(indent=2))
    if asset.geometry_kind == "points":
        print(
            "\nGeometry: point cloud (no faces). Segmentation and bite registration "
            "read points, but surface-dependent steps stay unavailable - re-export "
            "as a mesh model if you need them."
        )
    if asset.declared_units is not None:
        print(
            f"\nDeclared units: the file says {asset.declared_units.value}. "
            "Confirm scan units in the app before any measurement is trusted."
        )
    note = bounding_box_sanity(asset)
    print(f"\nScale note: {note}" if note else "\nScale note: none")
    return 0


def cmd_register_mesh(args: argparse.Namespace) -> int:
    try:
        asset = register_scan_mesh(
            args.path,
            workspace=args.workspace,
            provenance=MeshProvenance(args.provenance),
        )
    except (OSError, ValueError) as exc:
        print(f"register-mesh error: {exc}", file=sys.stderr)
        return 2
    print(asset.model_dump_json(indent=2))
    print(
        "\nAdd this asset id to a plan mesh_assets/tooth_meshes link, then run "
        "`orthoplan serve` with ORTHOPLAN_MESH_WORKSPACE pointing to the same workspace."
    )
    return 0


#: Retained name for callers that predate multi-format intake.
cmd_inspect_stl = cmd_inspect_scan
