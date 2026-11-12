"""Versioned local USER_ONE baseline labels, separate from published datasets."""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from threading import RLock

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID

_SAVE_LOCK = RLock()


def correction_store() -> Path:
    return Path(os.environ.get("ORTHOPLAN_REGION_CORRECTIONS", str(
        Path(__file__).resolve().parents[1] / ".orthoplan-region-corrections"
    )))


def baseline_source(arch: str) -> dict:
    if arch not in {"upper", "lower"}:
        raise ValueError("Choose upper or lower baseline.")
    filename = f"initial-{arch}.stl"
    manifest = json.loads((SAMPLE_CASE_DIR / "manifest.json").read_text())
    source = next(item for item in manifest["scans"] if item["filename"] == filename)
    if hashlib.sha256((SAMPLE_CASE_DIR / filename).read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("Baseline scan does not match its recorded hash.")
    return source


def validate_corrections(record: dict, arch: str, source: dict) -> dict:
    if not isinstance(record, dict) or set(record) != {
        "schema", "source_sha256", "arch", "face_count", "labels_base64", "reviewed", "provenance"
    }:
        raise ValueError("Invalid correction record fields.")
    if (record["schema"] != "ortho-region-corrections-v1" or record["arch"] != arch
            or record["source_sha256"] != source["sha256"]
            or type(record["face_count"]) is not int or record["face_count"] != source["face_count"]
            or type(record["reviewed"]) is not bool or record["provenance"] != "user-corrected"):
        raise ValueError("Corrections do not match this baseline scan and arch.")
    encoded = record["labels_base64"]
    if not isinstance(encoded, str) or len(encoded) != ((source["face_count"] + 2) // 3) * 4:
        raise ValueError("Correction label count is invalid.")
    try:
        labels = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Correction labels must be valid base64.") from exc
    pattern = r"[12][1-8]" if arch == "upper" else r"[34][1-8]"
    if len(labels) != source["face_count"] or any(id and not re.fullmatch(pattern, str(id)) for id in set(labels)):
        raise ValueError("Labels must use tooth numbers belonging to this arch.")
    if record["reviewed"] and not any(labels):
        raise ValueError("An empty label map cannot be marked reviewed.")
    return {"tooth_ids": sorted(set(labels) - {0}), "labeled_faces": sum(bool(id) for id in labels),
            "unlabeled_faces": labels.count(0)}


def _folder(root: Path, arch: str) -> Path:
    folder = root / "USER_ONE" / f"baseline-{arch}"
    if any(path.is_symlink() for path in [root, folder.parent, folder]):
        raise ValueError("Correction storage must not use symbolic links.")
    return folder


def save_baseline_corrections(payload: dict, *, root: Path | None = None) -> dict:
    with _SAVE_LOCK:
        if "base_saved_at" in payload:
            latest = load_baseline_corrections(payload.get("arch"), root=root)
            if not latest["ok"]:
                return latest
            if payload["base_saved_at"] != latest.get("saved_at"):
                return {"ok": False, "errors": [
                    "A newer draft is saved. Download JSON to keep these edits, then use Reload saved before continuing."
                ]}
        return _save_snapshot(payload, root=root)


def _save_snapshot(payload: dict, *, root: Path | None = None) -> dict:
    try:
        arch = payload.get("arch")
        source = baseline_source(arch)
        record = payload.get("corrections")
        summary = validate_corrections(record, arch, source)
        notes = payload.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError("Notes must be text of at most 4,000 characters.")
        timestamp = datetime.now(timezone.utc)
        snapshot = {"schema": "ortho-baseline-annotation-v1", "specimen_id": SAMPLE_SPECIMEN_ID,
                    "pseudonym": "USER_ONE", "visit": "initial", "filename": source["filename"],
                    "saved_at": timestamp.isoformat(), "notes": notes,
                    "review_status": "user-reviewed" if record["reviewed"] else "draft",
                    "summary": summary, "corrections": record}
        folder = _folder(root if root is not None else correction_store(), arch)
        folder.mkdir(parents=True, exist_ok=True)
        name = timestamp.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex + ".json"
        path = folder / name
        temporary = path.with_suffix(".tmp")
        try:
            with temporary.open("x") as handle:
                json.dump(snapshot, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return {"ok": True, "saved": True, "path": str(path.resolve()), **snapshot}
    except (ValueError, OSError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc) if isinstance(exc, ValueError) else "Could not save local corrections."]}


def load_baseline_corrections(arch: str, *, root: Path | None = None) -> dict:
    try:
        source = baseline_source(arch)
        folder = _folder(root if root is not None else correction_store(), arch)
        files = sorted(folder.glob("*.json"))
        if not files:
            return {"ok": True, "saved": False}
        path = files[-1]
        if path.is_symlink():
            raise ValueError("Correction snapshots must not be symbolic links.")
        snapshot = json.loads(path.read_text())
        if (snapshot.get("schema") != "ortho-baseline-annotation-v1"
                or snapshot.get("specimen_id") != SAMPLE_SPECIMEN_ID or snapshot.get("visit") != "initial"
                or snapshot.get("filename") != source["filename"]):
            raise ValueError("Saved annotations do not match this baseline.")
        validate_corrections(snapshot.get("corrections"), arch, source)
        return {**snapshot, "ok": True, "saved": True, "path": str(path.resolve())}
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        return {"ok": False, "errors": [str(exc) if isinstance(exc, ValueError) else "Could not read local corrections."]}
