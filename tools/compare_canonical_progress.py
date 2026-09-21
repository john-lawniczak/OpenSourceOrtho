"""Reproduce the canonical case's unregistered scan comparison.

Run from the repository root with numpy and matplotlib installed. The figure
uses view-only rotations and centering, never anatomical registration or scale
fitting. Source triangles are preserved; neither mesh is modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np


CASE = Path(__file__).resolve().parents[1] / "ui/example-scans/canonical-orthocad-001"
TRIANGLE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)),
                     ("attribute", "<u2")])


def read_triangles(path: Path, expected_sha256: str) -> np.ndarray:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Manifest hash mismatch: {path.name}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError(f"Expected exact binary STL length: {path.name}")
    vertices = np.frombuffer(raw, dtype=TRIANGLE, offset=84)["vertices"].astype(float)
    if not np.isfinite(vertices).all():
        raise ValueError(f"Non-finite scan coordinates: {path.name}")
    return vertices


def geometry_record(scan: dict, triangles: np.ndarray) -> dict:
    points = triangles.reshape(-1, 3)
    low, high = points.min(axis=0), points.max(axis=0)
    cross = np.cross(triangles[:, 1] - triangles[:, 0],
                     triangles[:, 2] - triangles[:, 0])
    return {
        "filename": scan["filename"], "sha256": scan["sha256"],
        "units": scan["units"], "face_count": len(triangles),
        "vertex_count": len(points),
        "vertex_count_definition": "Triangle-soup entries, not unique vertices",
        "bounds": {"min_xyz": low.tolist(), "max_xyz": high.tolist()},
        "extent_source_units": (high - low).tolist(),
        "degenerate_faces": int(np.count_nonzero(np.linalg.norm(cross, axis=1) == 0)),
    }


def draw_arch(ax, triangles: np.ndarray, rotation: list[int], title: str) -> None:
    # Each diagonal is a proper rotation (determinant +1), never a mirror.
    vertices = triangles * np.asarray(rotation)
    center = (vertices.min(axis=(0, 1)) + vertices.max(axis=(0, 1))) / 2
    vertices -= center
    normals = np.cross(vertices[:, 1] - vertices[:, 0],
                       vertices[:, 2] - vertices[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-12)
    light = np.array([-0.3, 0.4, 0.866])
    intensity = 0.45 + 0.55 * np.maximum(normals @ light, 0)
    colors = intensity[:, None] * np.array([0.78, 0.85, 0.88])
    order = np.argsort(vertices[:, :, 2].mean(axis=1), kind="stable")
    ax.add_collection(PolyCollection(vertices[order, :, :2],
                                    facecolors=colors[order], edgecolors="none"))
    ax.set(xlim=(-36, 36), ylim=(-31, 31), aspect="equal", title=title)
    ax.set_axis_off()


def main() -> None:
    manifest = json.loads((CASE / "manifest.json").read_text())
    scans = {s["filename"]: s for s in manifest["scans"]}
    # View-only camera orientation; source export transforms are not reapplied.
    views = [
        ("sample-test-case-upper.stl", [-1, 1, -1], "Upper | Baseline"),
        ("progress-01-upper.stl", [1, 1, 1], "Upper | Reported week 7"),
        ("sample-test-case-lower.stl", [1, 1, 1], "Lower | Baseline"),
        ("progress-01-lower.stl", [1, 1, 1], "Lower | Reported week 7"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 11), facecolor="white")
    records = []
    for ax, (filename, rotation, title) in zip(axes.flat, views):
        triangles = read_triangles(CASE / filename, scans[filename]["sha256"])
        records.append(geometry_record(scans[filename], triangles))
        draw_arch(ax, triangles, rotation, title)
    fig.suptitle("Baseline and first progress scan", fontsize=20, y=0.98)
    fig.text(0.5, 0.94, "June 5, 2026  →  September 17, 2026", ha="center", fontsize=12)
    fig.text(0.5, 0.045,
             "Independent occlusal views • equal source-coordinate scale • no registration\n"
             "User-confirmed week 7 • reported five-day tray changes • 30 calendar days after start\n"
             "Progress scale unverified.\n"
             "Surface appearance includes scan coverage and attachments; no tooth movement is measured.",
             ha="center", fontsize=10, linespacing=1.7)
    fig.subplots_adjust(top=0.90, bottom=0.12, hspace=0.14, wspace=0.05)
    fig.savefig(CASE / "progress-01-comparison.png", dpi=150)
    plt.close(fig)
    report = {
        "schema": "opensource-ortho-unregistered-scan-comparison-v1",
        "specimen_id": manifest["specimen_id"],
        "method": "Full binary STL triangle inventory and independent orthographic views",
        "generator": "tools/compare_canonical_progress.py",
        "registration_status": "not-validated",
        "coordinate_scale": "Source units; progress millimeter scale unverified",
        "scans": records,
        "display": {"projection": "XY, camera along positive Z",
                    "rotation_diagonals": {v[0]: v[1] for v in views},
                    "centering": "Independent bounding-box center; no scale fitting",
                    "axis_limits_source_units": [[-36, 36], [-31, 31]],
                    "rendering": "Depth-sorted triangles with normal-based shading"},
        "per_tooth_movement_mm": None,
        "tracking_error_mm": None,
        "limitations": [
            "Different export frames; no validated shared bite or cross-time registration",
            "Whole-arch shells include soft tissue, attachments, and scan coverage differences",
            "Triangle count and bounds changes describe files, not treatment effectiveness",
            "No final outcome, reviewed tooth correspondence, or verified progress scale",
        ],
    }
    (CASE / "progress-01-comparison.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
