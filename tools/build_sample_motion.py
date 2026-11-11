"""Build reproducible best-effort weekly motion previews from the public endpoint STLs.

Install the optional motion-preview extra; run from the repository root. No
private scans, remote inference, or manually authored target movements are used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.datasets import SAMPLE_CASE_DIR as CASE  # noqa: E402
from orthoplan.longitudinal.artifact import pack_face_labels  # noqa: E402
from orthoplan.longitudinal.preview import build_arch_preview, centered_triangles  # noqa: E402


TRIANGLE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)),
                     ("attribute", "<u2")])


def read_source(scan):
    raw = (CASE / scan["filename"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != scan["sha256"]:
        raise ValueError(f"Source hash mismatch: {scan['filename']}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError("Expected exact binary STL length")
    triangles = np.frombuffer(raw, dtype=TRIANGLE, offset=84)["vertices"].astype(float)
    if not np.isfinite(triangles).all():
        raise ValueError("Non-finite source geometry")
    return triangles


def main():
    manifest = json.loads((CASE / "manifest.json").read_text())
    display = json.loads((CASE / "derived/progress-01-comparison.json").read_text())["display"]
    records = {s["filename"]: s for s in manifest["scans"]}
    for arch, anatomical in [("upper", "maxillary"), ("lower", "mandibular")]:
        names = [f"initial-{arch}.stl", f"progress-01-{arch}.stl"]
        rotations = [display["rotation_diagonals"][name] for name in names]
        triangles = [centered_triangles(read_source(records[name]), rotation)
                     for name, rotation in zip(names, rotations)]
        preview = build_arch_preview(*triangles, arch=anatomical)
        preview.update(specimen_id=manifest["specimen_id"],
                       sources=[{"filename": name, "sha256": records[name]["sha256"],
                                 "rotation": rotation} for name, rotation in zip(names, rotations)],
                       generator="tools/build_sample_motion.py")
        pack_face_labels(preview)
        output = CASE / f"derived/progress-01-motion-{arch}.json"
        output.write_text(json.dumps(preview, indent=2, allow_nan=False) + "\n")
        print(f"{arch}: {len(preview['teeth'])} draft matches; "
              f"{sum(t['status'].startswith('estimated') for t in preview['teeth'])} fitted", flush=True)
        for tooth in preview["teeth"]:
            print(tooth["tooth"], tooth["target_tooth"], tooth["status"],
                  np.round(tooth["translation"], 3).tolist(), tooth["fit"], flush=True)


if __name__ == "__main__":
    main()
