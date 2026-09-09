"""CLI for checking whether a file carries OpenSourceOrtho's data watermark.

Answers "how do I know a file is watermarked" from the command line, without
needing to write a Python snippet: it reads the visible marker (STL solid
name / JSON ``watermark`` block), and for STL files also checks the hidden
geometry signature (see ``orthoplan/watermark.py``) against whatever
watermark id the visible marker names, or an explicit ``--id``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from orthoplan.watermark import CANARY_TOKEN, contains_canary, detect_geometry_signature

_SOLID_NAME_RE = re.compile(r"^solid\s+(\S+)", re.MULTILINE)
_WM_MARKER_RE = re.compile(r"__oso-wm:([0-9a-fA-F-]+)__")


def add_watermark_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "verify-watermark",
        help="check a file for OpenSourceOrtho's visible + hidden data watermark",
    )
    parser.add_argument("path", help="an exported .stl, a manifest .json, or any text file")
    parser.add_argument(
        "--id",
        default=None,
        help="candidate watermark id to check the STL geometry signature against "
        "(defaults to the id found in the visible solid-name marker, if any)",
    )


def cmd_verify_watermark(args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"verify-watermark error: {exc}", file=sys.stderr)
        return 2

    if path.suffix.lower() == ".stl" or raw.lstrip().startswith("solid "):
        return _verify_stl(raw, args.id)
    if path.suffix.lower() == ".json":
        return _verify_json(raw)
    return _verify_text(raw)


def _verify_stl(raw: str, candidate_id: str | None) -> int:
    solid_match = _SOLID_NAME_RE.search(raw)
    if solid_match is None:
        print("No 'solid <name>' line found - this does not look like ASCII STL.")
        return 1
    solid_name = solid_match.group(1)
    wm_match = _WM_MARKER_RE.search(solid_name)

    print(f"Solid name: {solid_name}")
    if wm_match:
        found_id = wm_match.group(1)
        print(f"Visible marker: FOUND  watermark_id={found_id}")
        print(f"Canary token present: {contains_canary(raw)}")
    else:
        found_id = None
        print("Visible marker: NOT FOUND (name may have been stripped/renamed)")

    check_id = candidate_id or found_id
    if check_id is None:
        print(
            "Hidden geometry signature: SKIPPED - no watermark id to check against. "
            "Pass --id <watermark_id> to check a specific candidate."
        )
        return 0 if wm_match else 1

    triangles = _parse_ascii_triangles(raw)
    if not triangles:
        print("Hidden geometry signature: SKIPPED - no vertex data parsed.")
        return 0

    score = detect_geometry_signature(triangles, check_id)
    verdict = "MATCH" if score >= 0.9 else ("NO MATCH" if score <= 0.1 else "INCONCLUSIVE")
    print(f"Hidden geometry signature ({len(triangles)} triangles checked): "
          f"{score:.0%} match for id {check_id} -> {verdict}")
    return 0 if verdict == "MATCH" else 1


def _verify_json(raw: str) -> int:
    try:
        data = json.loads(raw)
    except ValueError as exc:
        print(f"verify-watermark error: not valid JSON ({exc})", file=sys.stderr)
        return 2

    watermark = data.get("watermark") if isinstance(data, dict) else None
    if not isinstance(watermark, dict):
        print("No top-level 'watermark' field found in this JSON document.")
        print(f"Canary token present anywhere in the file: {contains_canary(raw)}")
        return 1

    print("Visible marker: FOUND")
    print(f"  watermark_id: {watermark.get('watermark_id')}")
    print(f"  canary matches repo's token: {watermark.get('canary') == CANARY_TOKEN}")
    print(f"  created_at: {watermark.get('created_at')}")
    print(f"  notice: {watermark.get('notice')}")
    return 0


def _verify_text(raw: str) -> int:
    found = contains_canary(raw)
    print(f"Canary token present: {found}")
    if not found:
        print("No OpenSourceOrtho watermark evidence found in this file.")
    return 0 if found else 1


def _parse_ascii_triangles(raw: str) -> list[tuple]:
    vertices: list[tuple[float, float, float]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("vertex"):
            continue
        parts = stripped.split()
        if len(parts) != 4:
            continue
        try:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            continue
    return [tuple(vertices[i : i + 3]) for i in range(0, len(vertices) - 2, 3)]
