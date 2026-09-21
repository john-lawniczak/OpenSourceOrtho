"""Build offline mobile visit previews from hash-verified canonical scan data.

Requires the same optional NumPy/Matplotlib dependencies as the comparison tool.
Run from any directory; both native apps package this shared output folder.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from compare_canonical_progress import CASE, draw_arch, read_triangles


OUTPUT = Path(__file__).resolve().parents[1] / "mobile/sample-history"


def build_history() -> dict:
    manifest = json.loads((CASE / "manifest.json").read_text())
    timeline = json.loads((CASE / "longitudinal-record.json").read_text())
    comparison = json.loads((CASE / "derived/progress-01-comparison.json").read_text())
    scans = {scan["filename"]: scan for scan in comparison["scans"]}
    visits = []
    for event_id, label, detail in [
        ("initial", "Baseline", "Pretreatment scan; acquisition date confirmed by contributor."),
        ("progress-01", "Week 7", "User-confirmed progress label with five-day tray changes."),
    ]:
        event = next(e for e in timeline["events"] if e["event_id"] == event_id)
        arches = [build_arch(scans[filename], comparison) for filename in event["files"]]
        visits.append({"id": event_id, "label": label, "date": event["date"],
                       "detail": detail, "arches": arches})
    return {
        "schema": "opensource-ortho-mobile-history-v1",
        "specimenId": manifest["specimen_id"],
        "pseudonym": manifest["pseudonym"],
        "title": "Sample history",
        "summary": f"{manifest['pseudonym']} · two observed scan visits.",
        "timing": f"{timeline['timing']['baseline_to_progress_days']} days between scans. "
                  f"{timeline['timing']['recorded_treatment_start_to_progress_days']} calendar "
                  "days from recorded treatment start to progress scan. Week 7 is the "
                  "contributor's progress label. Five-day changes are reported practice, "
                  "not a recommended schedule.",
        "limitation": "Independent views at equal source-coordinate scale. Progress scale "
                      "and cross-time registration are unverified; tooth movement is not measured.",
        "context": "38 trays planned. Earlier tray-5 report has no observation date. "
                   "Current tray per arch, schedule start date, and adherence are unknown.",
        "visits": visits,
        "events": [{"id": e["event_id"], "date": e.get("date") or "Date unknown",
                    "label": {"initial": "Baseline scan", "cbct": "CBCT record (not bundled)",
                              "treatment-start": "Reported treatment start",
                              "tray-report": "Historical tray-5 report",
                              "progress-01": "Week 7 progress scan",
                              "progress-01-export": "Progress export"}[e["event_id"]]}
                   for e in timeline["events"]],
    }


def build_arch(scan: dict, comparison: dict) -> dict:
    filename = scan["filename"]
    preview = Path(filename).stem + ".png"
    triangles = read_triangles(CASE / filename, scan["sha256"])
    rotation = comparison["display"]["rotation_diagonals"][filename]
    fig, ax = plt.subplots(figsize=(6, 5.2), facecolor="white")
    draw_arch(ax, triangles, rotation, "")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(OUTPUT / preview, dpi=140)
    plt.close(fig)
    return {"name": "Upper" if "upper" in filename else "Lower",
            "previewImage": preview, "filename": filename, "sha256": scan["sha256"],
            "faceCount": scan["face_count"], "zeroAreaFaces": scan["degenerate_faces"],
            "units": scan["units"], "displayRotation": rotation}


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "history.json").write_text(json.dumps(build_history(), indent=2) + "\n")
