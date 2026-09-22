"""Repository locations and published-asset resolution for contributed cases."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote

from orthoplan.model.dataset import read_manifest
from orthoplan.model.dataset_consent import read_consent


DATASETS_ROOT = Path(__file__).resolve().parents[1] / "datasets"
SAMPLE_SPECIMEN_ID = "spec-07b7031938c84b1a9c98517b8bc4cdd3"
SAMPLE_CASE_DIR = DATASETS_ROOT / SAMPLE_SPECIMEN_ID
SAMPLE_URL_ROOT = f"/datasets/{SAMPLE_SPECIMEN_ID}"


def resolve_published_asset(reference: str, *, root: Path | None = None) -> Path | None:
    """Resolve only explicitly published files; never serve local case records."""
    relative = unquote(reference).removeprefix("./").removeprefix("/")
    parts = relative.split("/")
    if len(parts) < 3 or parts[0] != "datasets":
        return None
    if not re.fullmatch(r"spec-[0-9a-f]{32}", parts[1]):
        return None
    asset = "/".join(parts[2:])
    if any(p in {"", ".", ".."} or p.startswith(".") for p in parts[2:]):
        return None
    if "\\" in asset or "\x00" in asset or "%" in asset:
        return None
    dataset_root = root if root is not None else DATASETS_ROOT
    case = dataset_root / parts[1]
    try:
        if case.is_symlink():
            return None
        # Do not follow links even when they point back inside the case folder.
        for path in [case / "manifest.json", case / "consent.json", case / asset]:
            if any(p.is_symlink() for p in [path, *path.parents] if p != dataset_root):
                return None
        manifest = read_manifest(case / "manifest.json")
        consent = read_consent(case / "consent.json")
        if not consent.matches_manifest(manifest) or manifest.specimen_id != parts[1]:
            return None
        if asset not in consent.public_assets:
            return None
        candidate = (case / asset).resolve()
        if candidate.is_relative_to(case.resolve()) and candidate.is_file():
            return candidate
    except (OSError, ValueError):
        pass
    return None
