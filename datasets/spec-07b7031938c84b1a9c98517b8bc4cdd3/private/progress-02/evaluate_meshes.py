"""Reproduce this private visit's topology inventory and independent views.

Run with the repository virtual environment; requires NumPy and Matplotlib.
Uses every source triangle. No repairs, tolerance welding, or registration.
"""

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

BUNDLE = Path(__file__).resolve().parent
ROOT = BUNDLE.parents[3]
sys.path.insert(0, str(ROOT))
from tools import check_sample_topology as topology  # noqa: E402
from tools.compare_canonical_progress import read_triangles  # noqa: E402


def draw_view(ax, triangles, axes, signs, title):
    vertices = triangles[:, :, axes] * np.array(signs)
    low, high = vertices.min(axis=(0, 1)), vertices.max(axis=(0, 1))
    vertices -= (low + high) / 2
    normals = np.cross(vertices[:, 1] - vertices[:, 0],
                       vertices[:, 2] - vertices[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-12)
    light = np.array([-0.3, 0.4, 0.866])
    intensity = 0.35 + 0.65 * np.abs(normals @ light)
    colors = intensity[:, None] * np.array([0.78, 0.85, 0.88])
    order = np.argsort(vertices[:, :, 2].mean(axis=1), kind="stable")
    ax.add_collection(PolyCollection(vertices[order, :, :2],
                                    facecolors=colors[order], edgecolors="none"))
    half = max(high[:2] - low[:2]) * 0.55
    ax.set(xlim=(-half, half), ylim=(-half, half), aspect="equal", title=title)
    ax.set_axis_off()


def main():
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    # Reuse the existing exact-coordinate inventory against this private bundle.
    topology.CASE = BUNDLE
    records = [topology.inspect(scan) for scan in manifest["scans"]]
    for scan, record in zip(manifest["scans"], records):
        record["units"] = scan["units"]
        record["extent_source_units"] = [
            high - low for low, high in zip(scan["bounds"]["min_xyz"],
                                           scan["bounds"]["max_xyz"])
        ]
    report = {
        "schema": "opensource-ortho-scan-topology-v1",
        "specimen_id": manifest["specimen_id"],
        "progress_record_id": "progress-02",
        "generator": "evaluate_meshes.py",
        "dependencies": {"numpy": np.__version__, "matplotlib": matplotlib.__version__},
        "method": "Exact-coordinate vertex deduplication, undirected edge incidence and connectivity, float64 triangle areas; all original triangles",
        "input_geometry_modified": False,
        "scans": records,
        "not_assessed": ["self-intersections", "vertex manifoldness", "winding consistency",
                         "scanner accuracy", "complete anatomical coverage", "physical scale",
                         "bite accuracy", "cross-time registration", "chip locations or dimensions"],
        "source_damage": {
            "status": "contributor-reported",
            "description": "Both hardened stone models were chipped; contributor attributes defects to poor model-making, not the actual teeth.",
            "affected_arches": ["maxillary", "mandibular"],
            "affected_regions": "Exact chip locations are unspecified.",
        },
        "display": {
            "file": "mesh-views.png", "projection": "Independent orthographic views",
            "camera_directions": ["+Z", "-Z", "+Y"],
            "centering": "Independent bounding-box centering for display only",
            "scale": "Each panel fitted independently; not a cross-scan scale comparison",
            "shading": "Two-sided normal shading; not a winding diagnostic",
        },
    }
    (BUNDLE / "mesh-quality.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(records, indent=2), flush=True)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), facecolor="white")
    views = [([0, 1, 2], [1, 1, 1], "+Z"),
             ([0, 1, 2], [-1, 1, -1], "-Z"),
             ([0, 2, 1], [1, -1, 1], "+Y")]
    for row, scan in enumerate(manifest["scans"]):
        triangles = read_triangles(BUNDLE / scan["filename"], scan["sha256"])
        for ax, (permutation, signs, direction) in zip(axes[row], views):
            draw_view(ax, triangles, permutation, signs, f'{scan["arch"]} | camera {direction}')
    fig.suptitle("USER_ONE | reported week 18 | original test scan surfaces", fontsize=18)
    fig.text(0.5, 0.025,
             "Both stone models were chipped; contributor reports model-making defects, not actual tooth defects.\n"
             "All triangles rendered; independent panel scale and centering; units unverified; no registration.",
             ha="center", fontsize=11)
    fig.subplots_adjust(top=0.91, bottom=0.09, hspace=0.12, wspace=0.03)
    fig.savefig(BUNDLE / "mesh-views.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
