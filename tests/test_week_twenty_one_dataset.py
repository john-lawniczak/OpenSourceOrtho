"""Published week 21 bytes and redacted record stay bound to explicit scope."""
import hashlib
import json

from orthoplan.datasets import SAMPLE_CASE_DIR
from orthoplan.model.dataset import read_manifest
from orthoplan.evaluation.finding import Finding, lint_finding


def test_week_twenty_one_assets_have_consent_and_no_identifying_export_records():
    visit = SAMPLE_CASE_DIR / "visits/progress-03"
    consent = json.loads((SAMPLE_CASE_DIR / "consent.json").read_text())
    assets = [name for name in consent["public_assets"] if name.startswith("visits/progress-03/")]
    assert len(assets) == 18
    assert all((SAMPLE_CASE_DIR / name).is_file() for name in assets)
    assert not any(name.endswith((".pdf", ".xml", ".html", ".zip")) for name in assets)
    for name in assets:
        if name.endswith((".json", ".md", ".py")):
            text = (SAMPLE_CASE_DIR / name).read_text()
            for identifier in ["332990378", "0CMJJ130", "Lawniczak", "Trogan", "052152", "Pineapple", "ccc5a1a8"]:
                assert identifier not in text
    source = json.loads((visit / "source-metadata.json").read_text())
    assert source["reported_week"] == 21
    assert source["scan_acquisition"]["date"] == "2026-11-23"
    assert source["export"]["scanner_model"] == "Element 5D"
    manifest = read_manifest(visit / "manifest.json")
    for scan in manifest.scans:
        raw = (visit / scan.filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == scan.sha256
        assert raw[:80] == b" " * 80
        assert scan.units == "unverified"
    for image in source["images"]:
        assert hashlib.sha256((visit / image["filename"]).read_bytes()).hexdigest() == image["sha256"]
    for finding in json.loads((visit / "quality-findings.json").read_text())["findings"]:
        lint_finding(Finding.model_validate(finding))
