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


def personal_model_asset(url_path, *, expected_sha256=None):
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
    expected = record["assets"][name]
    if expected_sha256 is not None and expected != expected_sha256:
        return None
    path = _path(name, bundle)
    if path is None:
        return None
    with path.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
            return None
    if name in {"summary.json", "dental-comparison.json"}:
        _lint_report(json.loads(path.read_text()))
    return path


# Reject malformed records independently. Never include exception text or paths
# in the public response; direct downloads still fail closed on validation errors.
_RECORD_ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError)


def _issue(issues, bundle):
    issues.append({"bundle": bundle,
                   "message": "A companion record could not be verified. Other records remain available."})


def _impression_record(prefix, issues):
    path = personal_model_asset(ASSET_PREFIX + prefix + "summary.json")
    if path is None:
        return None
    summary = json.loads(path.read_text())
    record = {key: summary[key] for key in ["reported_week", "label", "score", "score_scope",
              "capture_date", "impression_date", "captures", "findings", "acquisition_review"]}
    record["photos"] = []
    for photo in summary.get("photos", []):
        try:
            if not isinstance(photo["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", photo["sha256"]):
                raise ValueError("Photo metadata requires a SHA-256 digest")
            image = personal_model_asset(ASSET_PREFIX + prefix + photo["filename"],
                                         expected_sha256=photo["sha256"])
            if image is not None:
                record["photos"].append({key: photo[key] for key in
                    ["filename", "label", "sha256", "same_condition_as_scan", "confirmed_on"]})
        except _RECORD_ERRORS:
            _issue(issues, prefix + "photos")
    return {**record, "asset_prefix": prefix}


def impression_payload(issues=None):
    issues = [] if issues is None else issues
    records = []
    for prefix in reversed(IMPRESSION_ROUTES):
        try:
            record = _impression_record(prefix, issues)
            if record is not None:
                records.append(record)
        except _RECORD_ERRORS:
            _issue(issues, prefix)
    return records or None


def _cast_payload():
    path = personal_model_asset(ASSET_PREFIX + "summary.json")
    if path is None:
        return {"available": False}
    summary = json.loads(path.read_text())
    findings = [lint_finding(Finding.model_validate(item)).model_dump(mode="json")
                for item in summary["findings"]]
    return {"available": True, "reported_week": 21, "date": summary["date"],
            "models": summary["models"], "captures": summary["captures"],
            "acquisition_review": summary.get("acquisition_review"),
            "findings": findings, "publication_status": "contributor-authorized public companion records"}


def personal_model_payload():
    """A rejected companion does not hide independent records or dental history."""
    issues = []
    try:
        payload = _cast_payload()
    except _RECORD_ERRORS:
        payload = {"available": False}
        _issue(issues, "casts")
    impressions = impression_payload(issues)
    if impressions or payload["available"]:
        payload["impressions"] = impressions
    if issues:
        payload["issues"] = issues
    return payload
