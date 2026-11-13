"""Prepare USER_ONE's suggested week 18 painting surfaces from saved week 7 crowns.

Draft records/audits are private development artifacts. --save installs them as
local, unreviewed paintings only if no draft exists. No original mesh is modified.
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

CAPTURES = {"upper": "upper-clean", "lower": "fusion-h-4"}
OUTPUT = SAMPLE_CASE_DIR / "private/painting-seeds/week-18"


def prepare(arch):
    capture = CAPTURES[arch]
    current = load_baseline_corrections(arch, visit="progress-02", capture=capture)
    if not current["ok"] or current["saved"]:
        raise ValueError(f"{arch}: existing week 18 painting or read error; refusing to replace it")
    source_save = load_baseline_corrections(arch, visit="progress-01")
    if not source_save["ok"] or not source_save["saved"]:
        raise ValueError(f"{arch}: saved week 7 painting required")
    source_record = baseline_source(arch, "progress-01")
    target_record = baseline_source(arch, "progress-02", capture)
    source, target = read_triangles(source_record), read_triangles(target_record)
    labels = np.frombuffer(base64.b64decode(source_save["corrections"]["labels_base64"], validate=True), dtype=np.uint8)
    print(f"{arch}: fitting week 7 crowns to week 18 {capture}", flush=True)
    matrix, fit = fit_crowns(source, target, labels, wide=arch == "lower")
    absent = json.loads((SAMPLE_CASE_DIR / "treatment-context.json").read_text())["dentition"]["absent_fdi"]
    projected, projection = project_crowns(source, target, labels, matrix, [int(t) for t in absent])
    correction = {"schema": "ortho-region-corrections-v1", "source_sha256": target_record["sha256"],
                  "arch": arch, "face_count": len(projected), "labels_base64": base64.b64encode(projected).decode(),
                  "reviewed": False, "provenance": "automatic-draft"}
    summary = validate_corrections(correction, arch, target_record)
    report = {"schema": "ortho-projected-label-draft-v1", "arch": arch, "visit": "progress-02", "capture": capture,
              "status": "automatic-draft", "source_visit": "progress-01",
              "source_annotation_sha256": hashlib.sha256(Path(source_save["path"]).read_bytes()).hexdigest(),
              "source_hashes": {r["filename"]: r["sha256"] for r in (source_record, target_record)},
              "source_to_target": matrix.tolist(), "registration_fit": fit, **projection, **summary,
              "limitations": ["Projection of user-painted week 7 crowns; not verified tooth identity or anatomy.",
                              "Rigid whole-arch alignment does not compensate for all individual tooth movements.",
                              "Gray areas include context, model chips, weak matches and removed disconnected fragments.",
                              "Units are unverified. No source coordinates, face order or holes were changed."]}
    print(f"{arch}: {len(summary['tooth_ids'])} colored teeth, {summary['labeled_faces']} colored faces", flush=True)
    return correction, report


def install(arch, correction, report):
    if correction.get("reviewed") is not False or correction.get("provenance") != "automatic-draft":
        raise ValueError("Seed labels must remain an unreviewed automatic draft")
    return save_baseline_corrections({"arch": arch, "visit": "progress-02", "capture": CAPTURES[arch],
        "base_saved_at": None, "corrections": correction,
        "notes": "AUTOMATIC DRAFT: Your week 7 painted crowns were projected onto this suggested week 18 scan. "
        "Review every tooth number and boundary. Gray areas are context or uncertain; missing model surfaces were not filled. "
        f"Colored teeth: {', '.join(map(str, report['tooth_ids']))}."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="Install new drafts locally without replacing any save")
    parser.add_argument("--install-prepared", action="store_true", help="Install checked private drafts without refitting")
    args = parser.parse_args()
    if args.install_prepared and not args.save:
        parser.error("--install-prepared requires --save")
    if args.install_prepared:
        prepared = {arch: (json.loads((OUTPUT / f"{arch}-corrections.json").read_text()),
                          json.loads((OUTPUT / f"{arch}-report.json").read_text())) for arch in CAPTURES}
    else:
        prepared = {arch: prepare(arch) for arch in CAPTURES}
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for arch, (correction, report) in prepared.items():
            (OUTPUT / f"{arch}-corrections.json").write_text(json.dumps(correction) + "\n")
            (OUTPUT / f"{arch}-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if args.save:
        for arch, (correction, report) in prepared.items():
            result = install(arch, correction, report)
            if not result["ok"]:
                raise ValueError(result["errors"])
            print(f"Saved {result['path']}", flush=True)


if __name__ == "__main__":
    main()
