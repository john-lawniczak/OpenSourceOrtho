"""Explicit, consented companion-cast records with hash-bound downloads."""
import hashlib
import json
import re
from pathlib import Path

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset
from orthoplan.evaluation.finding import Finding, lint_finding

BUNDLE_RELATIVE = Path("visits/progress-03/personal-models")
ASSET_PREFIX = "/api/sample-personal-models/assets/"


def _path(name):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", name):
        return None
    reference = f"datasets/{SAMPLE_CASE_DIR.name}/{BUNDLE_RELATIVE.as_posix()}/{name}"
    return resolve_published_asset(reference, root=SAMPLE_CASE_DIR.parent)


def _index():
    path = _path("record-assets.json")
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
    record = _index()
    if record is None or name not in record["assets"]:
        return None
    path = _path(name)
    if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != record["assets"][name]:
        return None
    if name == "summary.json":
        for item in json.loads(path.read_text())["findings"]:
            lint_finding(Finding.model_validate(item))
    return path


def personal_model_payload():
    """Missing or revoked companion records do not affect dental observations."""
    path = personal_model_asset(ASSET_PREFIX + "summary.json")
    if path is None:
        return {"available": False}
    summary = json.loads(path.read_text())
    findings = [lint_finding(Finding.model_validate(item)).model_dump(mode="json")
                for item in summary["findings"]]
    # Return only this deliberately attached summary, never desktop paths or other records.
    return {"available": True, "reported_week": 21, "date": summary["date"],
            "models": summary["models"], "captures": summary["captures"],
            "findings": findings, "publication_status": "contributor-authorized public companion records"}
