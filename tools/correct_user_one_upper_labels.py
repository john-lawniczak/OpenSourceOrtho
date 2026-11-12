"""Reproduce a source-bound USER_ONE upper annotation draft; never edit scan bytes."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np


def correct_labels(triangles, labels, recipe):
    """Apply simultaneous identity changes and explicit posterior separator planes."""
    original = np.asarray(labels, dtype=np.uint8)
    centers = np.asarray(triangles).mean(axis=1)
    result = original.copy()
    for source, target in recipe["source_label_map"].items():
        result[original == int(source)] = target
    for group in recipe["posterior_groups"]:
        mask = np.isin(original, group["source_labels"])
        partition = np.zeros(len(original), dtype=int)
        for plane in group["separators"]:
            boundary = plane["y_origin"] + plane["slope"] * (centers[:, 0] - plane["x_origin"])
            partition += centers[:, 1] > boundary
        result[mask] = np.asarray(group["target_labels"])[partition[mask]]
    return result


def generate(case):
    folder = case / "annotations"
    before = json.loads((folder / "initial-upper-before-posterior-correction.json").read_text())
    recipe = json.loads((folder / "initial-upper-posterior-recipe.json").read_text())
    raw = (case / "initial-upper.stl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != before["source_sha256"] or digest != recipe["source_sha256"]:
        raise ValueError("Recipe and labels must match the original upper scan hash")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, offset=84)["vertices"].astype(float)
    labels = np.frombuffer(base64.b64decode(before["labels_base64"], validate=True), dtype=np.uint8)
    if len(labels) != len(triangles) or before["face_count"] != len(labels):
        raise ValueError("Face counts must match")
    updated = correct_labels(triangles, labels, recipe)
    record = {**before, "labels_base64": base64.b64encode(updated.tobytes()).decode(), "reviewed": False}
    (folder / "initial-upper-tooth-corrections.json").write_text(json.dumps(record, indent=2) + "\n")
    report = {"status": recipe["status"], "source_sha256": digest,
              "input_corrections_sha256": hashlib.sha256((folder / "initial-upper-before-posterior-correction.json").read_bytes()).hexdigest(),
              "output_corrections_sha256": hashlib.sha256((folder / "initial-upper-tooth-corrections.json").read_bytes()).hexdigest(),
              "changed_faces": int(np.count_nonzero(updated != labels)),
              "previous_labels": {str(n): int((labels == n).sum()) for n in np.unique(labels)},
              "updated_labels": {str(n): int((updated == n).sum()) for n in np.unique(updated)},
              "front_21_22_faces_preserved": bool(np.all(updated[np.isin(labels, [21, 22])] == labels[np.isin(labels, [21, 22])])),
              "unlabeled_faces_preserved": bool(np.all(updated[labels == 0] == 0)),
              "limitations": recipe["limitations"]}
    (folder / "initial-upper-posterior-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    print(json.dumps(generate(parser.parse_args().case), indent=2))
