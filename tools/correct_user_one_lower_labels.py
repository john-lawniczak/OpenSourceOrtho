"""Reproduce and audit USER_ONE lower-only labels without reading an upper scan."""
import base64
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orthoplan.segmentation.crown_outlines import measure_crowns, separate_crowns  # noqa: E402

CASE = ROOT / "datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3"
ORDER = [47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37]


def generate(case=CASE):
    folder = case / "annotations"
    recipe = json.loads((folder / "initial-lower-valley-recipe.json").read_text())
    before_bytes = (folder / "initial-lower-before-correction.json").read_bytes()
    if hashlib.sha256(before_bytes).hexdigest() != recipe["input_corrections_sha256"]:
        raise ValueError("Original lower annotation snapshot changed")
    before = json.loads(before_bytes)
    raw = (case / "initial-lower.stl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != recipe["source_sha256"] or digest != before["source_sha256"]:
        raise ValueError("Lower labels and recipe must match the original lower scan")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, offset=84)["vertices"].astype(float)
    prior = np.frombuffer(base64.b64decode(before["labels_base64"], validate=True), dtype=np.uint8)
    crowns = recipe["crowns"]
    if [c["fdi"] for c in crowns] != ORDER:
        raise ValueError("Expected the explicit 14-tooth lower order, excluding 38 and 48")
    labels, graph, cleanup = separate_crowns(triangles, prior, crowns)
    records = measure_crowns(triangles, labels, graph, crowns, recipe["user_reference_width_mm"])
    edges = graph.tocoo()
    crossing = (labels[edges.row] != labels[edges.col]) & (labels[edges.row] != 0) & (labels[edges.col] != 0)
    if set(labels) != {0, *ORDER} or any(t["connected_components"] != 1 for t in records) or crossing.any():
        raise ValueError("Lower labels failed count, connectivity or contact-buffer checks")
    record = {**before, "labels_base64": base64.b64encode(labels.tobytes()).decode(), "reviewed": False}
    (folder / "initial-lower-tooth-corrections.json").write_text(json.dumps(record, indent=2) + "\n")
    report = {"schema": "ortho-lower-label-audit-v1", "status": "draft-needs-boundary-review",
              "source_filename": "initial-lower.stl", "source_sha256": digest,
              "units": "mm (case manifest declaration; not independently calibrated)",
              "scan_geometry_modified": False, "tooth_order": ORDER,
              "width_method": "98th minus 2nd percentile of source vertices projected onto the local arch tangent between neighboring crown seeds; not clinical mesiodistal caliper width",
              "midline": recipe["midline"], "cleanup": cleanup,
              "labeled_faces": int(np.count_nonzero(labels)), "unlabeled_faces": int((labels == 0).sum()),
              "cross_label_shared_edges": int(crossing.sum() // 2),
              "limitations": recipe["limitations"], "teeth": records}
    (folder / "initial-lower-segmentation-report.json").write_text(json.dumps(report, indent=2) + "\n")
    write_tables(folder, report)
    return triangles, labels, report


def write_tables(folder, report):
    fields = ["fdi", "face_count", "connected_components", "estimated_width_mm", "full_projected_span_mm", "within_reference_range", "flags"]
    with (folder / "initial-lower-segmentation-report.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for tooth in report["teeth"]:
            row = {k: tooth[k] for k in fields}
            row["flags"] = "; ".join(row["flags"])
            writer.writerow(row)
    lines = ["# USER_ONE lower baseline — segmentation draft", "",
             "Only initial-lower.stl was processed; original scan geometry is unchanged.",
             "Exactly 14 labels, one manifold-edge-connected component per tooth; 38/48 absent.",
             "Contact buffers, overlapping outlines, discarded fragments and context remain unlabeled.", "",
             "![Lower-only Above and front inspection](initial-lower-segmentation-views.png)", "",
             "## Width and boundary uncertainty", "", report["width_method"] + ".",
             "Units use the case's declared mm scale. Bounds are conservative crown-mask estimates;",
             "anatomical gumlines, hidden contact surfaces and scale need review. No width-based resizing was applied.", "",
             "| FDI | Faces | Components | Estimated width (mm) | Supplied range (mm) | Check |",
             "| --- | ---: | ---: | ---: | --- | --- |"]
    for t in report["teeth"]:
        check = "Within supplied range; draft" if t["within_reference_range"] else "Outside supplied range; inspect extent/rotation"
        lines.append(f"| {t['fdi']} | {t['face_count']:,} | {t['connected_components']} | {t['estimated_width_mm']:.2f} | {t['user_reference_width_mm']} | {check} |")
    lines += ["", "## Midline and side convention", "", report["midline"]["assessment"], "",
              "The mirrored numbering order does not imply symmetric tooth positions or shapes.",
              "", "## Reproduce", "", "```bash",
              "python3 tools/correct_user_one_lower_labels.py", "```", "",
              "Recipe polygons follow estimated valleys/contact lines in the lower-only occlusal view.",
              "Every triangle corner must lie inside one outline and the previous crown mask.",
              "Contested faces and faces bridging labels are cleared. Only the largest connected",
              "component of each candidate remains. Connectivity is verified; anatomical precision is not.", ""]
    (folder / "initial-lower-segmentation-report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    _, _, result = generate()
    for tooth in result["teeth"]:
        print(tooth["fdi"], tooth["face_count"], tooth["estimated_width_mm"], tooth["within_reference_range"])
