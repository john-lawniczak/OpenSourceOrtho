"""CLI to emit a per-tooth crown-landmark template for the Generate Plan flow.

The template is a fill-in `ArchLandmarks` JSON: occlusal-plane (x, y) crown
centers in millimeters, one per tooth. Fill it from the scan (occlusal view),
set ``approximate`` to false once the coordinates are measured, and pass it to
the UI's "Import landmarks" control or the ``/api/generate-plan`` ``landmarks``
field. Precise landmarks raise plan fidelity above the approximate scaffold.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from orthoplan.model.landmarks import ArchLandmarks, CrownLandmark
from orthoplan.model.plan import ToothId

_UPPER = [f"1{p}" for p in range(1, 9)] + [f"2{p}" for p in range(1, 9)]
_LOWER = [f"4{p}" for p in range(1, 9)] + [f"3{p}" for p in range(1, 9)]


def add_landmarks_parser(sub: Any) -> None:
    parser = sub.add_parser(
        "landmarks-template",
        help="emit a fill-in per-tooth crown-landmark JSON template",
    )
    parser.add_argument("--arch", choices=["upper", "lower", "both"], default="both")
    parser.add_argument("--out", default=None, help="write template JSON to this path")


def _template(arch: str) -> ArchLandmarks:
    values = {"upper": _UPPER, "lower": _LOWER, "both": _UPPER + _LOWER}[arch]
    return ArchLandmarks(landmarks=[
        CrownLandmark(tooth=ToothId(value=v), x_mm=0.0, y_mm=0.0, approximate=True,
                      source="template - fill with measured occlusal-plane mm, then set approximate=false")
        for v in values
    ])


def cmd_landmarks_template(args: argparse.Namespace) -> int:
    template = _template(args.arch)
    body = template.model_dump_json(indent=2)
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(body + "\n", encoding="utf-8")
        print(f"Wrote landmark template ({len(template.landmarks)} teeth) to {args.out}", file=sys.stderr)
    else:
        print(body)
    return 0
