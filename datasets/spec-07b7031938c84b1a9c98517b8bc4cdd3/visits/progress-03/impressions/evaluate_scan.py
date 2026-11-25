"""Inventory original triangles and render views; no reconstruction or repair."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from matplotlib.collections import LineCollection
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from tools import check_sample_topology as topology
from tools.compare_canonical_progress import read_triangles

BUNDLE = Path(__file__).resolve().parent


def boundaries(triangles):
    points, faces = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = faces.reshape(-1, 3)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    edges, counts = np.unique(edges, axis=0, return_counts=True)
    edges = edges[counts == 1]
    vertices, indices = np.unique(edges, return_inverse=True)
    indices = indices.reshape(-1, 2)
    graph = coo_matrix((np.ones(len(indices)), (indices[:, 0], indices[:, 1])),
                       shape=(len(vertices), len(vertices)))
    count, labels = connected_components(graph, directed=False)
    components = []
    for index in range(count):
        group = edges[labels[indices[:, 0]] == index]
        selected = points[np.unique(group)]
        components.append({"edge_count": len(group), "length_source_units": float(
            np.linalg.norm(points[group[:, 0]] - points[group[:, 1]], axis=1).sum()),
            "bounds": {"min_xyz": selected.min(axis=0).tolist(),
                       "max_xyz": selected.max(axis=0).tolist()}})
    return points[edges], sorted(components, key=lambda row: row["edge_count"], reverse=True)


def render(triangles, edges, bundle, label):
    spec = importlib.util.spec_from_file_location(
        "impression_views", BUNDLE.parents[1] / "progress-02/evaluate_meshes.py")
    views = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(views)
    fig, axes = views.plt.subplots(2, 3, figsize=(18, 12))
    cameras = [([0, 1, 2], [1, 1, 1], "+Z"), ([0, 1, 2], [-1, 1, -1], "-Z"),
               ([0, 2, 1], [1, -1, 1], "+Y"), ([0, 2, 1], [1, 1, -1], "-Y"),
               ([1, 2, 0], [1, 1, 1], "+X"), ([1, 2, 0], [-1, 1, -1], "-X")]
    for ax, (permutation, signs, camera_label) in zip(axes.flat, cameras):
        views.draw_view(ax, triangles, permutation, signs, camera_label)
    fig.suptitle(f"Week 21 {label.lower()} | original exported surface | six views")
    fig.tight_layout()
    fig.savefig(bundle / "scan-overview.png", dpi=125)
    views.plt.close(fig)
    fig, axes = views.plt.subplots(1, 2, figsize=(16, 10))
    center = (triangles.min(axis=(0, 1)) + triangles.max(axis=(0, 1))) / 2
    for ax, signs, camera_label in zip(axes, [[1, 1, 1], [-1, 1, -1]], ["+Z", "-Z"]):
        views.draw_view(ax, triangles, [0, 1, 2], signs, camera_label + " | magenta: open boundary")
        lines = (edges - center) * signs
        ax.add_collection(LineCollection(lines[:, :, :2], colors="#d00080", linewidths=.9))
    fig.suptitle(f"{label} | original surface and projected open edges")
    fig.text(.5, .02, "Every boundary is projected, including edges behind the visible surface. "
             "Not a tooth segmentation or calibrated accuracy map.", ha="center")
    fig.savefig(bundle / "boundary-detail.png", dpi=160)
    views.plt.close(fig)


def main(bundle=BUNDLE, label="Upper impression 1"):
    scan = json.loads((bundle / "manifest.json").read_text())["scans"][0]
    triangles = read_triangles(bundle / scan["filename"], scan["sha256"])
    topology.CASE = bundle
    record = topology.inspect(scan)
    edges, components = boundaries(triangles)
    record.update(bounds=scan["bounds"], units="unverified", input_geometry_modified=False,
                  extent_source_units=np.ptp(triangles.reshape(-1, 3), axis=0).tolist(),
                  boundary_components=components,
                  method="Exact-coordinate deduplication, edge incidence and connectivity; all triangles.",
                  not_assessed=["self-intersections", "winding consistency", "anatomical accuracy",
                                "calibrated scale", "complete cavity coverage", "repeatability",
                                "registration to dental reference"])
    (bundle / "mesh-inventory.json").write_text(json.dumps(record, indent=2) + "\n")
    render(triangles, edges, bundle, label)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=BUNDLE)
    parser.add_argument("--label", default="Upper impression 1")
    args = parser.parse_args()
    main(args.bundle, args.label)
