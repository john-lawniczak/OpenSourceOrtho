"""CLI for registering contributed datasets under a tracked, PHI-free specimen id.

Kept out of ``cli.py`` so the contribution workflow (STL inspection + manifest
assembly) owns its own small module. The pure identity/manifest model lives in
``orthoplan/model/dataset.py``; this module does the file IO.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.io.stl_import import inspect_stl
from orthoplan.model.assets import MeshProvenance, MeshUnits
from orthoplan.model.dataset import (
    ContributedScan,
    DatasetManifest,
    new_specimen_id,
    write_manifest,
)


def add_contribution_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "register-contribution",
        help="register contributed STL scans under a tracked, PHI-free specimen id",
    )
    parser.add_argument("paths", nargs="+", help="one or more STL files")
    parser.add_argument(
        "--arch",
        choices=["maxillary", "mandibular"],
        default=None,
        help="arch the scan(s) belong to, if known",
    )
    parser.add_argument(
        "--units",
        choices=[u.value for u in MeshUnits],
        default=MeshUnits.UNVERIFIED.value,
        help="scan units (STL carries none; default unverified)",
    )
    parser.add_argument(
        "--provenance",
        choices=[p.value for p in MeshProvenance],
        default=MeshProvenance.PATIENT_DERIVED.value,
    )
    parser.add_argument("--notes", default=None, help="non-identifying notes only")
    parser.add_argument(
        "--i-confirm-no-phi",
        action="store_true",
        help="assert filenames/notes contain no patient-identifying information",
    )
    parser.add_argument("--out", default=None, help="write manifest JSON to this path")


def cmd_register_contribution(args: argparse.Namespace) -> int:
    if not args.i_confirm_no_phi:
        print(
            "register-contribution error: pass --i-confirm-no-phi to assert the "
            "files and notes contain no patient-identifying information.",
            file=sys.stderr,
        )
        return 2

    scans: list[ContributedScan] = []
    for path in args.paths:
        try:
            asset = inspect_stl(path, provenance=MeshProvenance(args.provenance))
        except (OSError, ValueError) as exc:
            print(f"register-contribution error: {exc}", file=sys.stderr)
            return 2
        scans.append(
            ContributedScan(
                filename=path,
                sha256=asset.sha256 or "",
                units=MeshUnits(args.units),
                provenance=MeshProvenance(args.provenance),
                arch=args.arch,
                vertex_count=asset.vertex_count,
                face_count=asset.face_count,
                bounds=asset.bounds,
            )
        )

    try:
        manifest = DatasetManifest(
            specimen_id=new_specimen_id(),
            scans=scans,
            consent_acknowledged=True,
            phi_removed=True,
            notes=args.notes,
        )
    except ValueError as exc:
        print(f"register-contribution error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        write_manifest(manifest, args.out)
        print(f"Registered {len(scans)} scan(s) as {manifest.specimen_id}")
        print(f"Wrote manifest to {args.out}")
    else:
        print(manifest.model_dump_json(indent=2))
    return 0
