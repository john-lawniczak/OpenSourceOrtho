"""Reproduce the lower-impression editorial review and verified download index."""
import hashlib
import json
from pathlib import Path

from orthoplan.evaluation.capture_review import review_manifest
from orthoplan.evaluation.finding import Finding, lint_finding
from orthoplan.model.dataset import read_manifest

BUNDLE = Path(__file__).resolve().parent
RUBRIC = [("File integrity/basic topology", 1.75, 2),
          ("Visible arch/cavity coverage", 2.75, 4),
          ("Visible local detail", 1.50, 2),
          ("Provenance, calibration and repeat evidence", .75, 2)]
OBSERVATIONS = [
    ("Same-condition photograph", "The contributor confirms the attached photograph shows this lower impression in the exact condition of the STL capture. A ragged material edge is visible at the upper-right end of the photograph. This is physical surface context, not proof that a specific mesh opening represents a tear or missing tooth-contact detail. Tall walls and shadow obscure some cavities. The 6.75 score remains provisional; separate optical gaps from physical irregularities before deciding what a repeat can recover."),
    ("Coverage", "The lower arch and anterior/posterior tooth cavities are recognizable in one connected mesh. Several elongated gaps interrupt side-wall coverage, including a large opening near the posterior end at the top-left of the +Z view. This scan retains useful exploratory acquisition evidence, but the wall coverage is less complete than the upper impression."),
    ("Open boundaries", "There are nine connected boundary groups: one large perimeter group and eight additional groups. The magenta overlay projects all open edges, including hidden surfaces; it does not identify eight missing teeth or assign anatomical left/right. The side views confirm visible wall openings. Not every open edge represents missing tooth-contact surface."),
    ("Detail limits", "Biting-surface patterns remain visible, but several narrow cavities and anterior transitions look rounded or locally irregular. This export cannot separate impression quality from optical capture or reconstruction effects. More triangles than the upper scan do not imply greater accuracy."),
    ("Rescan recommendation", "Keep this original and prioritize one targeted repeat of the lower over another upper scan. Capture the posterior-end opening and both side walls from different oblique angles while supporting the impression without flexing it. Preserve the repeat separately and compare coverage before any merging. If a gap is present in the physical impression, rescanning cannot restore that missing material."),
    ("Comparison with upper", "Using the same subjective rubric, the lower is 6.75/10.00 versus 7.50/10.00 for the upper. The lower loses 0.50 points for visible coverage and 0.25 for local detail. These are quarter-point editorial judgments displayed to two decimals, not measured anatomical accuracy or a clinical rating."),
    ("Provenance and limits", "The contributor confirms the same history as the upper: impression taken November 23, scanned November 24, no coating or manual edits in JMStudio. No raw scanner project was provided. Physical condition, storage effects, scale and internal scanner fusion remain unverified. This negative impression is not a direct tooth-motion observation; no dental-reference fit or bite registration was performed."),
]


def advisory(title, message):
    return lint_finding(Finding(severity="notice", category="data_gap", provenance="MODEL",
                                title=title, message=message)).model_dump(mode="json")


def report_text(summary, inventory):
    lines = ["# USER_ONE — week 21 lower impression", "",
             "**6.75/10.00 for exploratory scan usability.** Preserve this capture; a targeted repeat is recommended and has higher priority than repeating the upper impression. This is a subjective assessment, not a calibrated accuracy measurement.", "",
             "Contributor-confirmed impression date: November 23, 2026; capture: November 24; imported November 25. No coating or manual JMStudio edits. Original exported bytes unchanged.", "",
             "| Criterion | Points | Maximum |", "| --- | ---: | ---: |"]
    lines += [f"| {name} | {points:.2f} | {maximum:.2f} |" for name, points, maximum in RUBRIC]
    lines += ["", "[Physical lower impression photograph](lower-impression-photo.png). Same condition as the scan, explicitly confirmed November 25; photo acquisition date is unspecified. Embedded metadata was removed and orientation applied; decoded RGB pixels are preserved losslessly. Original photo remains local.", ""]
    lines += ["", "## Measured mesh properties", "",
              f"- {inventory['face_count']:,} triangles; {inventory['unique_vertices']:,} exact-coordinate unique vertices; one connected component.",
              f"- {inventory['zero_area_faces']} zero-area triangles; {inventory['duplicate_faces']} duplicate faces; {inventory['edges_with_more_than_two_incident_faces']} edges incident to more than two faces.",
              f"- {inventory['boundary_edges']:,} open edges in nine connected boundary groups; eight additional groups beyond the largest perimeter group. These are topology counts, not missing-tooth counts.",
              "- Extents: " + " × ".join(f"{v:.2f}" for v in inventory["extent_source_units"]) + " unverified source units.",
              "- No repairs, hole filling, smoothing, decimation, rescaling or normal reversal during this review.", ""]
    lines += [f"**{finding['title']}.** {finding['message']}\n" for finding in summary["findings"]]
    lines += ["## Inspect and reproduce", "",
              "See [six original-surface views](scan-overview.png) and [open-edge detail](boundary-detail.png). Patient-side orientation and individual tooth numbers have not been assigned. No registration to the dental scan, self-intersection analysis, calibrated scale check or independent repeatability check was performed. Upper and lower impression scans do not have an established shared bite frame.", "",
              "From the repository root:", "", "```sh",
              f"MPLCONFIGDIR=/private/tmp/ortho-matplotlib PYTHONPATH=. .venv/bin/python {BUNDLE.parent.relative_to(BUNDLE.parents[5])}/evaluate_scan.py --bundle {BUNDLE.relative_to(BUNDLE.parents[5])} --label 'Lower impression 1'",
              f"PYTHONPATH=. .venv/bin/python {BUNDLE.relative_to(BUNDLE.parents[5])}/build_assessment.py",
              "python3 tools/build_dataset_catalog.py", "```", ""]
    report = "\n".join(lines)
    advisory("Complete report language check", report)
    return report


def main():
    manifest = read_manifest(BUNDLE / "manifest.json")
    scan, = manifest.scans
    source = json.loads((BUNDLE / "source-metadata.json").read_text())
    inventory = json.loads((BUNDLE / "mesh-inventory.json").read_text())
    summary = {"schema": "opensource-ortho-impression-assessment-v1", "reported_week": 21,
               "label": "Lower impression 1", "score": sum(row[1] for row in RUBRIC),
               "score_scope": "subjective exploratory scan usability; not anatomical accuracy",
               "score_precision": "quarter-point editorial judgments, displayed to two decimals",
               "capture_date": source["capture_date"], "impression_date": source["impression_date"],
               "photos": source.get("photos", []),
               "captures": [{"filename": scan.filename, "sha256": scan.sha256}],
               "rubric": [{"category": name, "points": points, "maximum": maximum}
                          for name, points, maximum in RUBRIC],
               "findings": [advisory(title, message) for title, message in OBSERVATIONS],
               "acquisition_review": review_manifest(manifest)}
    (BUNDLE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (BUNDLE / "quality-assessment.md").write_text(report_text(summary, inventory))
    names = [scan.filename, "manifest.json", "source-metadata.json", "summary.json",
             "mesh-inventory.json", "scan-overview.png", "boundary-detail.png", "quality-assessment.md"]
    names += [photo["filename"] for photo in summary["photos"]]
    index = {"specimen_id": manifest.specimen_id, "progress_record_id": "progress-03",
             "assets": {name: hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest() for name in names}}
    (BUNDLE / "record-assets.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
