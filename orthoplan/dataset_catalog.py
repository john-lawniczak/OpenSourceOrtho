"""Build a deterministic public case catalog from validated manifests and scope."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid

from orthoplan.datasets import DATASETS_ROOT, SAMPLE_SPECIMEN_ID, resolve_published_asset
from orthoplan.model.dataset import infer_scan_labels, read_manifest
from orthoplan.model.dataset_consent import read_consent


def published_scans(case, manifest, consent):
    """Validate baseline and explicitly published supplementary visit manifests."""
    records = [(case, manifest)]
    for asset in consent.public_assets:
        if asset.startswith("visits/") and asset.endswith("/manifest.json"):
            visit = read_manifest(case / asset)
            if visit.specimen_id != manifest.specimen_id or visit.pseudonym != manifest.pseudonym:
                raise ValueError(f"Supplementary manifest identity mismatch: {asset}")
            if not consent.matches_manifest(visit):
                raise ValueError(f"Inconsistent supplementary publication scope: {asset}")
            records.append(((case / asset).parent, visit))
    scans = []
    for directory, record in records:
        for scan in record.scans:
            relative = str((directory / scan.filename).relative_to(case))
            if relative not in consent.public_assets:
                raise ValueError(f"Scan outside publication scope: {relative}")
            if hashlib.sha256((case / relative).read_bytes()).hexdigest() != scan.sha256:
                raise ValueError(f"Scan hash mismatch: {relative}")
            if directory == case and infer_scan_labels(scan.filename) != (scan.role, scan.arch, scan.sequence_index):
                raise ValueError(f"Scan labels disagree with standard filename: {relative}")
            scans.append(scan)
    return scans


def catalog_entry(case: Path) -> dict:
    manifest = read_manifest(case / "manifest.json")
    consent = read_consent(case / "consent.json")
    identity = uuid.UUID(hex=manifest.specimen_id.removeprefix("spec-"))
    if case.name != f"spec-{identity.hex}" or identity.version != 4:
        raise ValueError(f"Case folder must match its UUID4 specimen ID: {case.name}")
    if not manifest.pseudonym or not consent.matches_manifest(manifest):
        raise ValueError(f"Missing pseudonym or inconsistent publication scope: {case.name}")
    if consent.exact_dates_retained and not consent.date_retention_basis:
        raise ValueError(f"Date retention needs a documented basis: {case.name}")
    total_bytes = 0
    for asset in consent.public_assets:
        path = resolve_published_asset(f"/datasets/{case.name}/{asset}", root=case.parent)
        if path is None:
            raise ValueError(f"Missing or unsafe published asset: {case.name}/{asset}")
        total_bytes += path.stat().st_size
    visits: dict[tuple, set] = {}
    scans = published_scans(case, manifest, consent)
    for scan in scans:
        visits.setdefault((scan.role, scan.sequence_index), set()).add(scan.arch)
    return {
        "specimen_id": manifest.specimen_id, "uuid": str(identity),
        "pseudonym": manifest.pseudonym, "manifest": f"{case.name}/manifest.json",
        "overview": f"{case.name}/README.md",
        "roles_present": sorted({s.role for s in scans}),
        "scan_count": len(scans),
        "scan_pair_count": sum({"maxillary", "mandibular"} <= v for v in visits.values()),
        "has_cbct_metadata": "cbct-metadata.redacted.json" in consent.public_assets,
        "consent_acknowledged": consent.consent_acknowledged,
        "exact_dates_retained": consent.exact_dates_retained,
        "public_asset_count": len(consent.public_assets), "published_bytes": total_bytes,
    }


def build_catalog(root: Path = DATASETS_ROOT) -> dict:
    entries = [catalog_entry(p.parent) for p in sorted(root.glob("spec-*/manifest.json"))]
    pseudonyms = [e["pseudonym"] for e in entries]
    if len(pseudonyms) != len(set(pseudonyms)):
        raise ValueError("Pseudonyms must be unique in the public catalog")
    return {"schema": "opensource-ortho-dataset-index-v1", "cases": entries}


def catalog_readme(catalog: dict) -> str:
    lines = [
        "# Published research datasets", "",
        "Start here to browse contributed cases. Each UUID folder is the source of truth",
        "for one longitudinal case; a pseudonym is a readable label, not a person's name.",
        "The UUID is preserved across visits. No real-identity lookup is published.", "",
        "| Pseudonym | Specimen ID | Available scans | Scan pairs | CBCT metadata |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for entry in catalog["cases"]:
        label = f"[{entry['pseudonym']}]({entry['overview']})"
        roles = ", ".join(entry["roles_present"])
        cbct = "Redacted metadata only" if entry["has_cbct_metadata"] else "No"
        lines.append(f"| {label} | `{entry['specimen_id']}` | {roles} | {entry['scan_pair_count']} | {cbct} |")
    lines.extend([
        "", "## Layout and publication", "",
        "- `manifest.json` owns identity, pseudonym, scan roles, hashes, and summary metadata.",
        "- `consent.json` records publication scope and any exact-date retention exception.",
        "- Original STL files keep standard role/arch labels at the case root.",
        "- `media/` contains source renderings and reference media with their provenance.",
        "- `derived/` contains regenerable comparisons, topology reports, and transcriptions.",
        "- `fixtures/` contains engineering fixtures, not measured patient anatomy.",
        "- `visits/` contains explicitly approved supplementary visits and captures, each with its manifest.",
        "- `.local/` is ignored and never served; raw CBCT and private records stay there.",
        "", "Pseudonyms and UUIDs do not establish anonymity. Case dates remain only where",
        "their retention was explicitly requested. Existing reference-media rights caveats",
        "remain in force; a publication record does not create new permissions.", "",
        "The development server serves only paths listed in each case's `public_assets`",
        "and rejects traversal and symlinks. Private files do not become public by being",
        "placed inside a case folder. The catalog lists no acquisition dates or identities.",
        "", "## Add or update a case", "",
        "Follow [DATA_CONTRIBUTION.md](../docs/DATA_CONTRIBUTION.md). Keep the existing",
        "UUID for later visits and append progress records instead of replacing originals.",
        "After reviewing the manifest, pseudonym, scope, and files, regenerate this table",
        "and `index.json` with `python3 tools/build_dataset_catalog.py`.",
        "Use `--check` to verify generated outputs without modifying files.", "",
        "Original scans remain in Git; this reorganization does not decimate files, rewrite",
        "history, or introduce LFS. Apps package derived previews from the canonical cases.",
        "This is a clear-aligner planning safety playground and research toolkit.", "",
    ])
    return "\n".join(lines)


def browser_sample_module(catalog: dict) -> str:
    entry = next(e for e in catalog["cases"] if e["specimen_id"] == SAMPLE_SPECIMEN_ID)
    sample = {"specimenId": entry["specimen_id"], "pseudonym": entry["pseudonym"],
              "urlRoot": f"/datasets/{entry['specimen_id']}"}
    return ("// Generated by tools/build_dataset_catalog.py; do not edit.\n"
            f"export const sampleDataset = {json.dumps(sample, indent=2)};\n\n"
            "export function sampleAssetUrl(relative) {\n"
            "  return `${sampleDataset.urlRoot}/${relative}`;\n}\n\n"
            "export function sampleAssetReference(relative) {\n"
            "  return sampleAssetUrl(relative).slice(1);\n}\n")
