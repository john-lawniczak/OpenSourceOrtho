"""Seed local week 7 painting from saved week 1 crowns; never replace a saved draft.

Run with the motion-preview dependencies. Writes only ignored local snapshots and
an audit report. Original scans, baseline labels and motion artifacts stay intact.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.datasets import SAMPLE_CASE_DIR  # noqa: E402
from orthoplan.longitudinal.preview import centered_triangles  # noqa: E402
from orthoplan.longitudinal.projection import correspondence_mask  # noqa: E402
from orthoplan.longitudinal.registration import register_arches  # noqa: E402
from orthoplan.region_corrections import (  # noqa: E402
    baseline_source, correction_store, load_baseline_corrections, save_baseline_corrections,
)
from orthoplan.segmentation.topology import face_graph  # noqa: E402


def read_triangles(source):
    raw = (SAMPLE_CASE_DIR / source["filename"]).read_bytes()
    count = int.from_bytes(raw[80:84], "little")
    if (hashlib.sha256(raw).hexdigest() != source["sha256"]
            or count != source["face_count"] or len(raw) != 84 + count * 50):
        raise ValueError("Source hash or binary STL face count mismatch")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    return np.frombuffer(raw, dtype=dtype, offset=84)["vertices"].astype(float)


def prepare(arch):
    existing = load_baseline_corrections(arch, visit="progress-01")
    if not existing["ok"] or existing["saved"]:
        raise ValueError(f"{arch}: existing week 7 save or read error; refusing to replace it")
    baseline = load_baseline_corrections(arch)
    if not baseline["ok"] or not baseline["saved"]:
        raise ValueError(f"{arch}: saved baseline labels are required")
    records = [baseline_source(arch, visit) for visit in ["initial", "progress-01"]]
    display = json.loads((SAMPLE_CASE_DIR / "derived/progress-01-comparison.json").read_text())["display"]
    meshes = [centered_triangles(read_triangles(r), display["rotation_diagonals"][r["filename"]]) for r in records]
    source_labels = np.frombuffer(base64.b64decode(baseline["corrections"]["labels_base64"], validate=True), dtype=np.uint8)
    print(f"{arch}: fitting observed arches", flush=True)
    registration, metrics = register_arches(*meshes)
    nearest, valid, checks = correspondence_mask(*meshes, registration)
    labels = np.where(valid, source_labels[nearest], 0).astype(np.uint8)
    absent = json.loads((SAMPLE_CASE_DIR / "treatment-context.json").read_text())["dentition"]["absent_fdi"]
    labels[np.isin(labels, [int(t) for t in absent])] = 0
    graph = face_graph(meshes[1])
    edges = graph.tocoo()
    crossing = (labels[edges.row] != labels[edges.col]) & (labels[edges.row] != 0) & (labels[edges.col] != 0)
    buffer_faces = np.unique(np.r_[edges.row[crossing], edges.col[crossing]])
    labels[buffer_faces] = 0
    regions = []
    for tooth in sorted(set(source_labels) - {0}):
        faces = np.flatnonzero(labels == tooth)
        components, removed = 0, 0
        if len(faces):
            components, ids = connected_components(graph[faces][:, faces])
            discarded = faces[ids != np.bincount(ids).argmax()]
            labels[discarded] = 0
            removed = len(discarded)
        regions.append({"tooth": int(tooth), "faces": int((labels == tooth).sum()),
                        "components_before_cleanup": int(components), "discarded_fragment_faces": removed})
    report = {"schema": "ortho-projected-label-draft-v1", "arch": arch, "visit": "progress-01",
              "status": "automatic-draft", "baseline_snapshot": baseline["path"],
              "baseline_snapshot_sha256": hashlib.sha256(Path(baseline["path"]).read_bytes()).hexdigest(),
              "source_hashes": {r["filename"]: r["sha256"] for r in records},
              "target_to_source": registration.tolist(), "registration_fit": metrics,
              "correspondence_checks": checks, "contact_buffer_faces": len(buffer_faces), "teeth": regions,
              "labeled_faces": int(np.count_nonzero(labels)), "unlabeled_faces": int((labels == 0).sum()),
              "limitations": ["Automatic projection of unreviewed baseline crowns, not verified tooth identity.",
                              "Global rigid alignment can misplace boundaries where individual teeth moved.",
                              "Unmatched surfaces, contact buffers and disconnected fragments remain gray.",
                              "Original scan coordinates and face order are unchanged; source units are unverified."]}
    correction = {"schema": "ortho-region-corrections-v1", "source_sha256": records[1]["sha256"],
                  "arch": arch, "face_count": len(labels), "labels_base64": base64.b64encode(labels).decode(),
                  "reviewed": False, "provenance": "automatic-draft"}
    print(f"{arch}: {sum(t['faces'] > 0 for t in regions)} colored regions, {report['labeled_faces']} labeled faces", flush=True)
    return correction, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="Save drafts locally after preparing both arches")
    args = parser.parse_args()
    prepared = {arch: prepare(arch) for arch in ["upper", "lower"]}
    folder = correction_store() / "USER_ONE" / ("week-7-seed-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    folder.mkdir(parents=True, exist_ok=False)
    for arch, (correction, report) in prepared.items():
        path = folder / f"{arch}-report.json"
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        (folder / f"{arch}-corrections.json").write_text(json.dumps(correction) + "\n")
        if args.save:
            result = save_baseline_corrections({"arch": arch, "visit": "progress-01", "base_saved_at": None,
                "corrections": correction, "notes": "AUTOMATIC DRAFT: Week 1 saved crowns projected onto the observed week 7 mesh using rigid alignment, distance/normal/round-trip checks and connected-region cleanup. Review every tooth number and boundary; gray regions are context or uncertain. Audit: " + str(path)})
            if not result["ok"]:
                raise ValueError(result["errors"])
            print(f"Saved {result['path']}", flush=True)
    print(f"Audit folder: {folder}")


if __name__ == "__main__":
    main()
