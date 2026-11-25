"""Capture provenance must not turn damaged or appliance surfaces into teeth."""
import argparse
import hashlib
import json

import pytest
from pydantic import ValidationError

from orthoplan.cli_capture import cmd_review_captures
from orthoplan.evaluation.capture_review import review_capture, review_manifest
from orthoplan.evaluation.finding import Finding, lint_finding
from orthoplan.model.capture import CaptureProvenance
from orthoplan.model.dataset import ContributedScan, DatasetManifest, read_manifest, write_manifest


def scan(filename="capture.stl", sha256="a" * 64, **capture):
    return ContributedScan(filename=filename, sha256=sha256, vertex_count=3, face_count=1,
                           acquisition=CaptureProvenance(**capture) if capture else None)


@pytest.mark.parametrize("capture", [
    {"kind": "aligner_scan", "surface": "dentition"},
    {"kind": "impression_scan", "surface": "dentition"},
    {"condition": "intact", "fragment_count": 2},
    {"condition": "reassembled", "fragment_count": 1},
    {"coating": "none", "coating_product": "paint"},
    {"parent_sha256": ["a source filename"]},
    {"physical_object_id": "../../private"},
])
def test_conflicting_or_invalid_provenance_is_rejected(capture):
    with pytest.raises(ValidationError):
        CaptureProvenance(**capture)


@pytest.mark.parametrize("kind,surface,code", [
    ("aligner_scan", "appliance_inner", "Appliance proxy"),
    ("aligner_scan", "appliance_outer", "Appliance proxy"),
    ("impression_scan", "negative_impression", "Negative impression"),
    ("printed_model_scan", "dentition", "Printed-model proxy"),
])
def test_proxy_geometry_stays_explorable_without_becoming_arch_reference(kind, surface, code):
    review = review_capture(scan(kind=kind, surface=surface, condition="intact", coating="none"))
    assert review["interpretation"] == code
    assert review["intact_arch_reference"] == "excluded"
    assert review["exploratory_inspection_permitted"]
    for finding in review["findings"]:
        lint_finding(Finding.model_validate(finding))


def test_unknown_legacy_record_and_reassembled_cast_never_gain_reference_status():
    unknown = review_capture(scan())
    assert unknown["kind"] == "unknown"
    assert unknown["intact_arch_reference"] == "excluded"
    broken = review_capture(scan(kind="cast_scan", surface="dentition", condition="reassembled",
                                 fragment_count=2, support_material="clay"))
    assert broken["intact_arch_reference"] == "excluded"
    unspecified = review_capture(scan(kind="cast_scan", fragment_count=2))
    assert unspecified["intact_arch_reference"] == "excluded"
    assert any(item["code"] == "capture.damage" for item in broken["findings"])
    declared = review_capture(scan(kind="intraoral_scan", surface="dentition", condition="intact"))
    assert declared["intact_arch_reference"] == "not_established"


def test_repeat_exports_and_sessions_do_not_prove_independence():
    a = scan("a.stl", physical_object_id="cast-one", capture_session_id="one", kind="cast_scan")
    b = scan("b.stl", physical_object_id="cast-one", capture_session_id="two", kind="cast_scan")
    c = scan("c.stl", "b" * 64, physical_object_id="cast-one", kind="cast_scan")
    d = scan("d.stl", physical_object_id="cast-two", kind="cast_scan")
    group, = review_manifest(DatasetManifest(scans=[a, b, c, d]))["repeat_groups"]
    assert group["capture_count"] == 3
    assert group["distinct_file_count"] == 2
    assert group["recorded_session_count"] == 2
    assert group["independence"] == "not_established"


@pytest.fixture
def manifest_path(tmp_path):
    raw = b"synthetic untouched scan"
    (tmp_path / "capture.stl").write_bytes(raw)
    path = tmp_path / "manifest.json"
    write_manifest(DatasetManifest(scans=[scan(sha256=hashlib.sha256(raw).hexdigest(),
                                              kind="impression_scan", surface="negative_impression")]), path)
    return path


def test_review_roundtrip_checks_original_hash_and_keeps_proxy_type(manifest_path, capsys):
    args = argparse.Namespace(manifest=manifest_path, out=None)
    assert read_manifest(manifest_path).scans[0].acquisition.kind == "impression_scan"
    assert cmd_review_captures(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scan_hashes_verified"]
    assert payload["records"][0]["intact_arch_reference"] == "excluded"
    (manifest_path.parent / "capture.stl").write_bytes(b"modified")
    assert cmd_review_captures(args) == 2
    assert "hash mismatch" in capsys.readouterr().err


@pytest.mark.parametrize("filename", ["manifest.json", "capture.stl"])
def test_review_cannot_overwrite_source(manifest_path, filename):
    target = manifest_path.parent / filename
    previous = target.read_bytes()
    assert cmd_review_captures(argparse.Namespace(manifest=manifest_path, out=target)) == 2
    assert target.read_bytes() == previous


def test_symlink_scan_is_not_followed(manifest_path):
    path = manifest_path.parent / "capture.stl"
    moved = path.with_name("elsewhere.stl")
    path.rename(moved)
    path.symlink_to(moved)
    assert cmd_review_captures(argparse.Namespace(manifest=manifest_path, out=None)) == 2
