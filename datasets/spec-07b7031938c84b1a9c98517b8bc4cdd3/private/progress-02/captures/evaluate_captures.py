"""Compare the two additional lower captures without modifying source geometry.

Run with the repository virtual environment; requires NumPy and Matplotlib.
Original November 10 pair reports remain separate. No registration or repair.
"""

import json
from pathlib import Path
import sys

BUNDLE = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE.parent))
from evaluate_meshes import draw_view  # noqa: E402
import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from tools import check_sample_topology as topology  # noqa: E402
from tools.compare_canonical_progress import read_triangles  # noqa: E402

CAPTURES = ("fusion-h-4", "fusion-h-6")


def inspect_captures():
    scans, records = [], []
    for capture in CAPTURES:
        manifest = json.loads((BUNDLE / capture / "manifest.json").read_text())
        scan = dict(manifest["scans"][0])
        scan["filename"] = f'{capture}/{scan["filename"]}'
        topology.CASE = BUNDLE
        record = topology.inspect(scan)
        record["units"] = scan["units"]
        record["extent_source_units"] = [
            high - low for low, high in zip(scan["bounds"]["min_xyz"],
                                           scan["bounds"]["max_xyz"])
        ]
        scans.append(scan)
        records.append(record)
    return scans, records


def render_views(scans):
    fig, axes = plt.subplots(len(scans), 3, figsize=(15, 10), facecolor="white")
    views = [([0, 1, 2], [1, 1, 1], "+Z"),
             ([0, 1, 2], [-1, 1, -1], "-Z"),
             ([0, 2, 1], [1, -1, 1], "+Y")]
    for row, scan in enumerate(scans):
        triangles = read_triangles(BUNDLE / scan["filename"], scan["sha256"])
        for ax, (permutation, signs, direction) in zip(axes[row], views):
            capture = Path(scan["filename"]).parent.name
            title = f'USER_ONE lower | week 18 | {capture}\nFiled 2026-11-12 | camera {direction}'
            draw_view(ax, triangles, permutation, signs, title)
    fig.suptitle("USER_ONE | reported week 18 | additional lower captures", fontsize=18)
    fig.text(0.5, 0.025,
             "All source triangles; independent panel centering and scale; units unverified.\n"
             "Same lower model; contributor reports a small front-tooth chip, exact location/timing unknown.",
             ha="center", fontsize=11)
    fig.subplots_adjust(top=0.91, bottom=0.09, hspace=0.12, wspace=0.03)
    fig.savefig(BUNDLE / "mesh-views.png", dpi=120)
    plt.close(fig)


def main():
    scans, records = inspect_captures()
    parent = json.loads((BUNDLE.parent / "source-metadata.json").read_text())
    damage = {
        capture: json.loads((BUNDLE / capture / "source-metadata.json").read_text())["capture"]["source_model_damage"]
        for capture in CAPTURES
    }
    report = {
        "schema": "opensource-ortho-scan-topology-v1",
        "specimen_id": parent["specimen_id"], "progress_record_id": "progress-02",
        "capture_ids": list(CAPTURES), "generator": "evaluate_captures.py",
        "dependencies": {"numpy": np.__version__, "matplotlib": matplotlib.__version__},
        "method": "Exact-coordinate vertex deduplication; undirected edge incidence and vertex connectivity; float64 triangle areas; all original triangles",
        "input_geometry_modified": False, "scans": records,
        "source_model_damage": damage,
        "not_assessed": ["self-intersections", "vertex manifoldness", "winding consistency",
                         "scanner accuracy", "anatomical fidelity", "complete anatomical coverage",
                         "physical scale", "bite accuracy", "cross-time registration",
                         "capture method", "chip location and timing", "repair or trimming history"],
        "display": {
            "file": "mesh-views.png", "projection": "Independent orthographic views",
            "camera_directions": ["+Z", "-Z", "+Y"],
            "centering": "Independent bounding-box centering for display only",
            "scale": "Each panel fitted independently; not a cross-scan scale comparison",
            "shading": "Two-sided normal shading; approximate depth sorting",
        },
    }
    (BUNDLE / "mesh-quality.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(records, indent=2), flush=True)
    render_views(scans)


if __name__ == "__main__":
    main()
