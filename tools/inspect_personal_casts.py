"""Inventory an unmodified cast bundle and render orthographic views."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tools import check_sample_topology as topology
from tools.compare_canonical_progress import read_triangles


def geometry_fingerprint(triangles):
    vertices, faces = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = np.sort(faces.reshape(-1, 3), axis=1)
    faces = faces[np.lexsort(faces.T[::-1])]
    return hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()


def inspect(bundle):
    manifest = json.loads((bundle / "source-metadata.json").read_text())
    case = bundle.parents[2]
    renderer = case / "visits/progress-02/evaluate_meshes.py"
    spec = importlib.util.spec_from_file_location("cast_views", renderer)
    views = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(views)
    topology.CASE = bundle
    records = []
    fig, axes = plt.subplots(6, 3, figsize=(15, 25), facecolor="white")
    cameras = [([0, 1, 2], [1, 1, 1], "+Z"),
               ([0, 2, 1], [1, -1, 1], "+Y"),
               ([1, 2, 0], [1, 1, 1], "+X")]
    for row, scan in enumerate(manifest["captures"]):
        triangles = read_triangles(bundle / scan["filename"], scan["sha256"])
        record = topology.inspect(scan)
        record.update(capture_id=scan["capture_id"], model_id=scan["model_id"],
                      geometry_sha256=geometry_fingerprint(triangles),
                      extent_source_units=np.ptp(triangles.reshape(-1, 3), axis=0).tolist())
        records.append(record)
        for ax, (permutation, signs, direction) in zip(axes[row], cameras):
            views.draw_view(ax, triangles, permutation, signs, f'{scan["capture_id"]} | {direction}')
        print(json.dumps(record), flush=True)
    fig.suptitle("USER_ONE week 21 | six personal cast scans, four physical casts", fontsize=18)
    fig.text(.5, .015, "Original surfaces; each panel fitted independently. Cast chips are contributor-reported.\n"
             "Unverified source units; no repairs, scale correction, or bite registration.", ha="center")
    fig.subplots_adjust(top=.96, bottom=.05, hspace=.1, wspace=.02)
    fig.savefig(bundle / "cast-overview.png", dpi=110)
    plt.close(fig)
    report = {"schema": "opensource-ortho-cast-inventory-v1", "input_geometry_modified": False,
              "method": "Exact-coordinate vertex deduplication and edge incidence; original triangles.",
              "scans": records, "not_assessed": ["self-intersections", "anatomical accuracy", "verified physical scale"]}
    (bundle / "mesh-inventory.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    inspect(parser.parse_args().bundle.resolve())
