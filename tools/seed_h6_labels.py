"""Prepare a private, unreviewed H6 draft from source-bound H4 crown labels.

No surface bytes or existing paintings are changed. --save installs only when
original H6 has no saved painting. Edited H6 copies retain their separate saves.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.datasets import SAMPLE_CASE_DIR  # noqa: E402
from orthoplan.region_corrections import (  # noqa: E402
    baseline_source, load_baseline_corrections, save_baseline_corrections, validate_corrections,
)
from tools.seed_week_seven_labels import read_triangles  # noqa: E402
from tools.week_eighteen_seed_geometry import fit_crowns, project_crowns  # noqa: E402

OUTPUT = SAMPLE_CASE_DIR / "private/painting-seeds/week-18-h6"


def prepare():
    current = load_baseline_corrections("lower", visit="progress-02", capture="fusion-h-6")
    if not current["ok"] or current["saved"]:
        raise ValueError("Existing H6 painting or read error; refusing to replace it")
    saved = load_baseline_corrections("lower", visit="progress-02", capture="fusion-h-4")
    if not saved["ok"] or not saved["saved"]:
        raise ValueError("Saved H4 crown labels are required")
    source_record = baseline_source("lower", "progress-02", "fusion-h-4")
    target_record = baseline_source("lower", "progress-02", "fusion-h-6")
    validate_corrections(saved["corrections"], "lower", source_record)
    source, target = read_triangles(source_record), read_triangles(target_record)
    labels = np.frombuffer(base64.b64decode(saved["corrections"]["labels_base64"], validate=True), dtype=np.uint8)
    print("Fitting original H4 crown regions to original H6; scans stay unchanged.", flush=True)
    matrix, fit = fit_crowns(source, target, labels, wide=True)
    absent = json.loads((SAMPLE_CASE_DIR / "treatment-context.json").read_text())["dentition"]["absent_fdi"]
    projected, projection = project_crowns(source, target, labels, matrix, [int(t) for t in absent])
    correction = {"schema": "ortho-region-corrections-v1", "source_sha256": target_record["sha256"],
                  "arch": "lower", "face_count": len(projected),
                  "labels_base64": base64.b64encode(projected).decode(),
                  "reviewed": False, "provenance": "automatic-draft"}
    summary = validate_corrections(correction, "lower", target_record)
    report = {"schema": "ortho-projected-label-draft-v1", "arch": "lower", "visit": "progress-02",
              "capture": "fusion-h-6", "source_capture": "fusion-h-4", "status": "automatic-draft",
              "source_annotation_sha256": hashlib.sha256(Path(saved["path"]).read_bytes()).hexdigest(),
              "source_hashes": {r["filename"]: r["sha256"] for r in (source_record, target_record)},
              "source_to_target": matrix.tolist(), "registration_fit": fit, **projection, **summary,
              "limitations": ["H4 draft labels projected onto H6, not independent reference labels.",
                              "Contributor suspects a model chip near FDI 32 and protruding material in H6; inspect these regions.",
                              "Reported JMStudio export units are mm; these exact files remain independently uncalibrated.",
                              "No source coordinates, triangle order, model defects or holes were changed.",
                              "This is painting preparation, not a tooth-motion or repeatability report."]}
    return correction, report


def install(correction, report):
    if correction.get("reviewed") is not False or correction.get("provenance") != "automatic-draft":
        raise ValueError("The H6 seed must remain an unreviewed automatic draft")
    return save_baseline_corrections({"arch": "lower", "visit": "progress-02", "capture": "fusion-h-6",
        "base_saved_at": None, "corrections": correction,
        "notes": "AUTOMATIC DRAFT: H4 crown labels projected onto original H6. Check every number and boundary before review. "
        "Contributor suspects model chip at FDI 32 (H4 appearance differs from H6); H6 also has protruding model material. "
        "Physical model reported unchanged between captures. Inspect 32 and excess material; do not treat either scan as ground truth. "
        "Gray includes context and uncertain matches; missing surfaces were not filled. "
        "JMStudio export units reported as millimetres; exact-file calibration not independently verified. "
        f"Draft teeth: {', '.join(map(str, report['tooth_ids']))}."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--install-prepared", action="store_true")
    args = parser.parse_args()
    if args.install_prepared and not args.save:
        parser.error("--install-prepared requires --save")
    if args.install_prepared:
        correction = json.loads((OUTPUT / "lower-corrections.json").read_text())
        report = json.loads((OUTPUT / "lower-report.json").read_text())
    else:
        correction, report = prepare()
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "lower-corrections.json").write_text(json.dumps(correction) + "\n")
        (OUTPUT / "lower-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"H6: {len(report['tooth_ids'])} draft teeth; {report['labeled_faces']} painted faces.", flush=True)
    if args.save:
        result = install(correction, report)
        if not result["ok"]:
            raise ValueError(result["errors"])
        print(f"Saved {result['path']}", flush=True)


if __name__ == "__main__":
    main()
