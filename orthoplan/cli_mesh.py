"""CLI for STL inspection and local mesh-workspace registration.

Grouped out of ``cli.py`` so the mesh commands own a small module, keeping the
top-level dispatcher focused and within the maintainability size guardrails.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.io.stl_import import inspect_stl
from orthoplan.mesh_workspace import register_stl_mesh
from orthoplan.model.assets import MeshProvenance, bounding_box_sanity


def add_mesh_parsers(sub: Any) -> None:
    inspect = sub.add_parser("inspect-stl", help="show units-unverified STL metadata")
    inspect.add_argument("path")
    inspect.add_argument(
        "--provenance",
        choices=[p.value for p in MeshProvenance],
        default=MeshProvenance.PATIENT_DERIVED.value,
    )

    register = sub.add_parser("register-mesh", help="copy an STL into the local mesh workspace")
    register.add_argument("path")
    register.add_argument("--workspace", default=None, help="mesh workspace directory")
    register.add_argument(
        "--provenance",
        choices=[p.value for p in MeshProvenance],
        default=MeshProvenance.IMPORTED.value,
    )


def cmd_inspect_stl(args: argparse.Namespace) -> int:
    try:
        asset = inspect_stl(args.path, provenance=MeshProvenance(args.provenance))
    except (OSError, ValueError) as exc:
        print(f"inspect-stl error: {exc}", file=sys.stderr)
        return 2
    print(asset.model_dump_json(indent=2))
    note = bounding_box_sanity(asset)
    print(f"\nScale note: {note}" if note else "\nScale note: none")
    return 0


def cmd_register_mesh(args: argparse.Namespace) -> int:
    try:
        asset = register_stl_mesh(
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
