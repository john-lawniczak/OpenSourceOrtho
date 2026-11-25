"""Deterministic capture interpretation; never infer anatomy from proxy surfaces."""
from collections import defaultdict

from orthoplan.evaluation.finding import Finding, lint_finding
from orthoplan.model.capture import CaptureProvenance

SCOPES = {
    "intraoral_scan": ("Observed intraoral surface", "An intraoral surface observation; anatomical fidelity still requires review."),
    "cast_scan": ("Cast-derived proxy", "Distances combine impression, casting, scanning and fitting effects."),
    "impression_scan": ("Negative impression", "A negative impression is not a positive tooth mesh. Flipping normals does not recover unseen recesses."),
    "aligner_scan": ("Appliance proxy", "Tray thickness, forming, relief and wear prevent treating the surface as actual teeth or the original target setup."),
    "printed_model_scan": ("Printed-model proxy", "Printing and post-processing add dimensional uncertainty; retain the originating digital model separately."),
    "unknown": ("Unclassified capture", "Capture method is unknown; do not infer it from the STL filename or appearance."),
}


def _finding(code, title, message):
    return lint_finding(Finding(severity="notice", category="data_gap", provenance="RULE",
                               code=code, title=title, message=message)).model_dump(mode="json")


def review_capture(scan):
    capture = scan.acquisition or CaptureProvenance()
    label, explanation = SCOPES[capture.kind]
    findings = [_finding("capture.kind", label, explanation)]
    damaged = (capture.condition in {"chipped", "fractured", "reassembled"}
               or (capture.fragment_count or 1) > 1)
    if damaged:
        label = "Damaged specimen / " + label
        findings.append(_finding("capture.damage", "Physical damage", "Missing surfaces or unverified fragment positions prevent interpreting this specimen as an intact-arch reference. Rescanning cannot restore missing anatomy."))
    if capture.coating != "none":
        findings.append(_finding("capture.coating", "Surface preparation", "Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth."))
    if capture.surface == "unknown":
        findings.append(_finding("capture.surface", "Surface identity", "The measured side of the object is unspecified; identify positive dentition, negative impression, or appliance inner/outer surface."))
    if capture.condition == "unknown":
        findings.append(_finding("capture.condition", "Specimen condition", "Physical condition has not been recorded; mesh connectivity does not establish an intact specimen."))
    if capture.processing:
        findings.append(_finding("capture.processing", "Processing history", "Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces."))
    if str(scan.units) != "mm":
        findings.append(_finding("capture.units", "Unverified scale", "Distances remain source-coordinate units until scale is independently established; this review does not change units."))
    else:
        findings.append(_finding("capture.units", "Declared scale", "The manifest declares millimeters. This metadata review does not independently verify physical scale."))
    return {"filename": scan.filename, "sha256": scan.sha256, "kind": capture.kind,
            "interpretation": label, "physical_object_id": capture.physical_object_id,
            "capture_session_id": capture.capture_session_id,
            "intact_arch_reference": "excluded" if damaged or capture.kind in {
                "impression_scan", "aligner_scan", "printed_model_scan", "unknown"} else "not_established",
            "exploratory_inspection_permitted": True, "findings": findings}


def review_manifest(manifest):
    records = [review_capture(scan) for scan in manifest.scans]
    groups = defaultdict(list)
    for record in records:
        if record["physical_object_id"]:
            groups[record["physical_object_id"]].append(record)
    repeated = []
    for identity, rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        repeated.append({"physical_object_id": identity,
                         "filenames": [row["filename"] for row in rows],
                         "capture_count": len(rows),
                         "distinct_file_count": len({row["sha256"] for row in rows}),
                         "recorded_session_count": len({row["capture_session_id"] for row in rows
                                                        if row["capture_session_id"]}),
                         "independence": "not_established",
                         "note": "Different hashes or session labels do not prove independent captures or anatomical accuracy."})
    return {"schema": "opensource-ortho-capture-review-v1", "records": records,
            "repeat_groups": repeated,
            "scope": "Declared provenance and research interpretation only; geometry, parent artifacts and clinical use are not validated."}
