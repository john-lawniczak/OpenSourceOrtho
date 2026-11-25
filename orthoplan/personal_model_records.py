"""Explicit, consented companion-cast records with hash-bound downloads."""
import hashlib
import json
import re
from pathlib import Path

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset
from orthoplan.evaluation.finding import Finding, lint_finding

BUNDLE_RELATIVE = Path("visits/progress-03/personal-models")
IMPRESSION_BUNDLE = Path("visits/progress-03/impressions")
IMPRESSION_ROUTES = {"impressions/lower/": IMPRESSION_BUNDLE / "lower",
                     "impressions/": IMPRESSION_BUNDLE}
ASSET_PREFIX = "/api/sample-personal-models/assets/"


def _lint_report(summary):
    findings = list(summary.get("findings", []))
    for record in summary.get("acquisition_review", {}).get("records", []):
        findings.extend(record["findings"])
    for item in findings:
        lint_finding(Finding.model_validate(item))


def _path(name, bundle=BUNDLE_RELATIVE):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", name):
        return None
    reference = f"datasets/{SAMPLE_CASE_DIR.name}/{bundle.as_posix()}/{name}"
    return resolve_published_asset(reference, root=SAMPLE_CASE_DIR.parent)


def _index(bundle=BUNDLE_RELATIVE):
    path = _path("record-assets.json", bundle)
    if path is None:
        return None
    record = json.loads(path.read_text())
    if record["specimen_id"] != SAMPLE_CASE_DIR.name or record["progress_record_id"] != "progress-03":
        raise ValueError("Companion record identity mismatch")
    return record


def personal_model_asset(url_path):
    name = url_path.removeprefix(ASSET_PREFIX)
    if not url_path.startswith(ASSET_PREFIX):
        return None
    bundle = BUNDLE_RELATIVE
    for prefix, target in IMPRESSION_ROUTES.items():
        if name.startswith(prefix):
            bundle, name = target, name.removeprefix(prefix)
            break
    record = _index(bundle)
    if record is None or name not in record["assets"]:
        return None
    path = _path(name, bundle)
    if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != record["assets"][name]:
        return None
    if name in {"summary.json", "dental-comparison.json"}:
        _lint_report(json.loads(path.read_text()))
    return path


def impression_payload():
    records = []
    for prefix in reversed(IMPRESSION_ROUTES):
        path = personal_model_asset(ASSET_PREFIX + prefix + "summary.json")
        if path is None:
            continue
        summary = json.loads(path.read_text())
        record = {key: summary[key] for key in ["reported_week", "label", "score", "score_scope",
                  "capture_date", "impression_date", "captures", "findings", "acquisition_review"]}
        record["photos"] = []
        for photo in summary.get("photos", []):
            image = personal_model_asset(ASSET_PREFIX + prefix + photo["filename"])
            if image is not None and hashlib.sha256(image.read_bytes()).hexdigest() == photo["sha256"]:
                record["photos"].append({key: photo[key] for key in
                    ["filename", "label", "sha256", "same_condition_as_scan", "confirmed_on"]})
        records.append({**record, "asset_prefix": prefix})
    return records or None


def personal_model_payload():
    """Missing or revoked companion records do not affect dental observations."""
    path = personal_model_asset(ASSET_PREFIX + "summary.json")
    impressions = impression_payload()
    if path is None:
        return {"available": False, **({"impressions": impressions} if impressions else {})}
    summary = json.loads(path.read_text())
    findings = [lint_finding(Finding.model_validate(item)).model_dump(mode="json")
                for item in summary["findings"]]
    # Return only this deliberately attached summary, never desktop paths or other records.
    return {"available": True, "reported_week": 21, "date": summary["date"],
            "models": summary["models"], "captures": summary["captures"],
            "acquisition_review": summary.get("acquisition_review"),
            "impressions": impressions,
            "findings": findings, "publication_status": "contributor-authorized public companion records"}
