"""Published week 21 bytes and redacted record stay bound to explicit scope."""
import hashlib
import json
import pytest

from orthoplan.datasets import SAMPLE_CASE_DIR
from orthoplan.model.dataset import read_manifest
from orthoplan.evaluation.finding import Finding, lint_finding


def test_week_twenty_one_assets_have_consent_and_no_identifying_export_records():
    visit = SAMPLE_CASE_DIR / "visits/progress-03"
    consent = json.loads((SAMPLE_CASE_DIR / "consent.json").read_text())
    assets = [name for name in consent["public_assets"] if name.startswith("visits/progress-03/")
              and "/personal-models/" not in name]
    assert len(assets) == 41  # 18 dental records plus 23 impression assets, including photos.
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


def test_personal_cast_originals_and_fracture_provenance_are_public():
    relative = "visits/progress-03/personal-models/"
    bundle = SAMPLE_CASE_DIR / relative
    consent = json.loads((SAMPLE_CASE_DIR / "consent.json").read_text())
    assets = [name for name in consent["public_assets"] if name.startswith(relative)]
    assert len(assets) == 17
    assert set(assets) == {relative + path.name for path in bundle.iterdir() if path.is_file()}
    manifest = read_manifest(bundle / "manifest.json")
    source = json.loads((bundle / "source-metadata.json").read_text())
    assert len(manifest.scans) == len(source["captures"]) == 6
    assert source["physical_model_count"] == 4
    for scan in manifest.scans:
        assert hashlib.sha256((bundle / scan.filename).read_bytes()).hexdigest() == scan.sha256
        assert scan.units == "unverified"
    c6 = next(scan for scan in source["captures"] if scan["capture_id"] == "lower-2-c6")
    assert c6["intact_arch_reference"] is False
    assert "clay" in c6["physical_state"]
    damage = source["source_model_damage"]["lower_model_2_update"]
    assert damage["fracture_piece_count"] == 2
    assert damage["assembly_alignment"] == "unverified"


@pytest.mark.parametrize("subfolder,expected_hash,arch", [
    ("", "40136020e7bc2ea06dba511191d765a7b05c7bf393230f075b780e86913d5f79", "maxillary"),
    ("lower", "a57ee3564fa08ce08fb5ed9dc591a74c86def63ea2f579256ed9f7f51f14fda4", "mandibular"),
])
def test_impression_original_and_dates_are_separate_from_dental_observation(subfolder, expected_hash, arch):
    bundle = SAMPLE_CASE_DIR / "visits/progress-03/impressions" / subfolder
    manifest = read_manifest(bundle / "manifest.json")
    scan, = manifest.scans
    assert hashlib.sha256((bundle / scan.filename).read_bytes()).hexdigest() == scan.sha256
    assert scan.sha256 == expected_hash
    assert scan.arch == arch
    assert scan.acquisition.kind == "impression_scan"
    assert scan.acquisition.surface == "negative_impression"
    assert scan.acquisition.coating == "none"
    assert scan.acquisition.processing == []
    assert str(scan.acquisition.acquired_on) == "2026-11-24"
    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["impression_date"] == "2026-11-23"
    assert summary["score"] == sum(row["points"] for row in summary["rubric"])
    assert summary["acquisition_review"]["records"][0]["intact_arch_reference"] == "excluded"
    for finding in summary["findings"]:
        lint_finding(Finding.model_validate(finding))
    history = json.loads((SAMPLE_CASE_DIR / "longitudinal-record.json").read_text())
    visit = next(row for row in history["events"] if row["event_id"] == "progress-03")
    assert visit["companion_impressions"]["capture_date"] == "2026-11-24"
    assert visit["companion_impressions"]["scan_count"] == 2
    assert len(visit["files"]) == 2
    assert all("impression" not in filename for filename in visit["files"])
    photo, = summary["photos"]
    assert photo["same_condition_as_scan"] and photo["confirmed_on"] == "2026-11-25"
    assert photo["photographed_on"] is None
    assert hashlib.sha256((bundle / photo["filename"]).read_bytes()).hexdigest() == photo["sha256"]


@pytest.mark.parametrize("subfolder,filename", [("", "upper-impression-photo.png"),
                                               ("lower", "lower-impression-photo.png")])
def test_impression_photographs_have_no_embedded_metadata(subfolder, filename):
    image = pytest.importorskip("PIL.Image")
    with image.open(SAMPLE_CASE_DIR / "visits/progress-03/impressions" / subfolder / filename) as photo:
        assert photo.format == "PNG" and photo.size == (3024, 4032)
        assert not photo.info and not photo.getexif()
