"""CLI for registering contributed datasets under a tracked, PHI-free specimen id.

Kept out of ``cli.py`` so the contribution workflow (STL inspection + manifest
assembly) owns its own small module. The pure identity/manifest model lives in
``orthoplan/model/dataset.py``; this module does the file IO.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from orthoplan.io.stl_import import inspect_stl
from orthoplan.model.assets import MeshProvenance, MeshUnits
from orthoplan.model.dataset import (
    ContributedScan,
    DatasetManifest,
    ScanRole,
    infer_scan_labels,
    new_specimen_id,
    read_plan_summary,
    text_has_phi_marker,
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
        help="fallback arch for scan(s) when it cannot be inferred from filename",
    )
    parser.add_argument(
        "--role",
        choices=["initial", "progress", "refinement", "final", "unknown"],
        default=None,
        help="fallback scan role when it cannot be inferred from filename",
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
        "--plan-summary",
        default=None,
        help="optional non-proprietary plan-summary.json sidecar to validate and include",
    )
    parser.add_argument(
        "--outcome-notes",
        default=None,
        help="optional outcome-notes.md sidecar; filename and hash are included",
    )
    parser.add_argument(
        "--i-confirm-no-phi",
        action="store_true",
        help="assert filenames/notes contain no patient-identifying information",
    )
    parser.add_argument("--out", default=None, help="write manifest JSON to this path")


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_from_path(path: str, args: argparse.Namespace) -> ContributedScan:
    asset = inspect_stl(path, provenance=MeshProvenance(args.provenance))
    inferred_role, inferred_arch, sequence_index = infer_scan_labels(path)
    role: ScanRole = args.role or inferred_role
    arch = args.arch or inferred_arch
    return ContributedScan(
        filename=path,
        role=role,
        sequence_index=sequence_index,
        sha256=asset.sha256 or "",
        units=MeshUnits(args.units),
        provenance=MeshProvenance(args.provenance),
        arch=arch,
        vertex_count=asset.vertex_count,
        face_count=asset.face_count,
        bounds=asset.bounds,
    )


def _validated_plan_summary(path: str | None):
    if not path:
        return None
    return read_plan_summary(path)


def _outcome_notes_sha256(path: str | None) -> str | None:
    if not path:
        return None
    notes_text = Path(path).read_text(encoding="utf-8")
    if text_has_phi_marker(notes_text):
        raise ValueError("outcome notes contain patient-identifying field markers")
    return _sha256_file(path)


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
            scans.append(_scan_from_path(path, args))
        except (OSError, ValueError) as exc:
            print(f"register-contribution error: {exc}", file=sys.stderr)
            return 2

    try:
        plan_summary = _validated_plan_summary(args.plan_summary)
        outcome_notes_sha256 = _outcome_notes_sha256(args.outcome_notes)
    except (OSError, ValueError) as exc:
        print(f"register-contribution error: {exc}", file=sys.stderr)
        return 2

    try:
        manifest = DatasetManifest(
            specimen_id=new_specimen_id(),
            scans=scans,
            plan_summary=plan_summary,
            plan_summary_filename=args.plan_summary,
            outcome_notes_filename=args.outcome_notes,
            outcome_notes_sha256=outcome_notes_sha256,
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
        print(manifest.model_dump_json(indent=2, by_alias=True))
    return 0
