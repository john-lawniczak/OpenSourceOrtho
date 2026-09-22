"""Catalog integrity and publication boundaries after dataset relocation."""

import hashlib
import json
from pathlib import Path
import uuid

import pytest

from orthoplan.dataset_catalog import build_catalog, browser_sample_module, catalog_readme
from orthoplan.datasets import DATASETS_ROOT, SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID, resolve_published_asset
from orthoplan.model.dataset import ContributedScan, DatasetManifest, write_manifest
from orthoplan.model.dataset_consent import DatasetConsent


def _case(root: Path, pseudonym: str = "USER_TEST") -> Path:
    case = root / f"spec-{uuid.uuid4().hex}"
    case.mkdir(parents=True)
    raw = b"test scan bytes"
    (case / "initial-upper.stl").write_bytes(raw)
    (case / "README.md").write_text("Case overview")
    scan = ContributedScan(filename="initial-upper.stl", role="initial", arch="maxillary",
                           sha256=hashlib.sha256(raw).hexdigest(), vertex_count=3, face_count=1)
    write_manifest(DatasetManifest(specimen_id=case.name, pseudonym=pseudonym, scans=[scan],
                                   consent_acknowledged=True, phi_removed=True), case / "manifest.json")
    consent = DatasetConsent(specimen_id=case.name, consent_acknowledged=True, phi_removed=True,
                             authorization_basis="Synthetic test", publication_scope=["test"],
                             public_assets=["initial-upper.stl", "README.md", "manifest.json", "consent.json"],
                             third_party_reference_rights="not-applicable", rights_note="Test fixture")
    (case / "consent.json").write_text(consent.model_dump_json(by_alias=True, indent=2))
    return case


def test_catalog_outputs_are_current_and_identity_is_preserved():
    catalog = build_catalog()
    assert json.loads((DATASETS_ROOT / "index.json").read_text()) == catalog
    assert (DATASETS_ROOT / "README.md").read_text() == catalog_readme(catalog)
    assert (DATASETS_ROOT.parent / "ui/sample-dataset.js").read_text() == browser_sample_module(catalog)
    entry = next(e for e in catalog["cases"] if e["specimen_id"] == SAMPLE_SPECIMEN_ID)
    assert entry["pseudonym"] == "USER_ONE"
    assert entry["uuid"] == "07b70319-38c8-4b1a-9c98-517b8bc4cdd3"
    assert entry["scan_pair_count"] == 2
    assert "2026-" not in json.dumps(catalog)


def test_catalog_rejects_changed_scan_bytes_and_duplicate_pseudonyms(tmp_path):
    case = _case(tmp_path)
    assert build_catalog(tmp_path)["cases"][0]["scan_count"] == 1
    _case(tmp_path)
    with pytest.raises(ValueError, match="Pseudonyms must be unique"):
        build_catalog(tmp_path)
    (case / "initial-upper.stl").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_catalog(tmp_path)


@pytest.mark.parametrize("relative", [
    ".local/secret.json", "records/volume.dcm", "private.json", "../index.json",
    "%2e%2e/index.json", "%252e%252e/index.json", "derived/../../manifest.json",
    "derived//report.json", "derived\\report.json", "media/reference-simulation.mp4",
])
def test_only_explicit_published_assets_resolve(relative):
    assert resolve_published_asset(f"/datasets/{SAMPLE_SPECIMEN_ID}/{relative}") is None


def test_revoked_scope_and_symlinks_are_rejected(tmp_path):
    case = _case(tmp_path)
    ref = f"/datasets/{case.name}/initial-upper.stl"
    assert resolve_published_asset(ref, root=tmp_path) == case / "initial-upper.stl"
    target = case / "initial-upper.stl"
    target.unlink()
    outside = tmp_path / "private.stl"
    outside.write_bytes(b"private geometry")
    target.symlink_to(outside)
    assert resolve_published_asset(ref, root=tmp_path) is None
    target.unlink()
    target.write_bytes(b"test scan bytes")
    consent = json.loads((case / "consent.json").read_text())
    consent["consent_acknowledged"] = False
    (case / "consent.json").write_text(json.dumps(consent))
    assert resolve_published_asset(ref, root=tmp_path) is None
    with pytest.raises(ValueError, match="publication scope"):
        build_catalog(tmp_path)


def test_dataset_http_and_segmentation_use_the_same_allowlist():
    from orthoplan.segmentation_api import _resolve_scan_path
    from orthoplan.server import Handler

    handler = Handler.__new__(Handler)
    ui_root = DATASETS_ROOT.parent / "ui"
    public = f"/datasets/{SAMPLE_SPECIMEN_ID}/initial-upper.stl"
    private = f"/datasets/{SAMPLE_SPECIMEN_ID}/.local/local-cbct-record.json"
    assert handler._resolve_static(public) == SAMPLE_CASE_DIR / "initial-upper.stl"
    assert _resolve_scan_path(public, ui_dir=ui_root, workspace=None) == SAMPLE_CASE_DIR / "initial-upper.stl"
    assert handler._resolve_static(private) is None
    assert _resolve_scan_path(private, ui_dir=ui_root, workspace=None) is None
    image = f"/datasets/{SAMPLE_SPECIMEN_ID}/media/progress-01-front.jpg"
    assert handler._resolve_static(image) == SAMPLE_CASE_DIR / "media/progress-01-front.jpg"
    assert _resolve_scan_path(image, ui_dir=ui_root, workspace=None) is None


@pytest.mark.parametrize("path", ["../secret", "/secret", ".local/secret", "records/file", "a//b"])
def test_consent_rejects_unsafe_asset_paths(path, tmp_path):
    case = _case(tmp_path)
    consent = json.loads((case / "consent.json").read_text())
    consent["public_assets"] = [path]
    with pytest.raises(ValueError):
        DatasetConsent.model_validate(consent)
