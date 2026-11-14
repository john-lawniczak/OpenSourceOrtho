"""Immutable local research records, kept outside published datasets."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from orthoplan.hashing import canonical_json, sha256_text

KINDS = {"fits", "reviews", "benchmarks"}


def folder(kind):
    if kind not in KINDS:
        raise ValueError("Unknown research record kind")
    root = Path(
        os.environ.get(
            "ORTHOPLAN_RESEARCH_STORE",
            str(Path(__file__).resolve().parents[1] / ".orthoplan-research"),
        )
    )
    path = root / kind
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("Research storage cannot follow symbolic links")
    return path


def save_record(kind, data):
    record = {**data, "id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat()}
    target = folder(kind)
    target.mkdir(parents=True, exist_ok=True)
    envelope = {"record": record, "sha256": sha256_text(canonical_json(record))}
    temporary = target / (record["id"] + ".tmp")
    with temporary.open("x") as handle:
        json.dump(envelope, handle, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target / (record["id"] + ".json"))
    return record


def read_record(kind, identity):
    if not re.fullmatch(r"[0-9a-f]{32}", identity):
        raise ValueError("Invalid record ID")
    path = folder(kind) / (identity + ".json")
    if path.is_symlink():
        raise ValueError("Research records cannot be symbolic links")
    envelope = json.loads(path.read_text())
    record = envelope["record"]
    if record.get("id") != identity or sha256_text(canonical_json(record)) != envelope.get(
        "sha256"
    ):
        raise ValueError("Research record integrity check failed")
    return record


def records(kind):
    return sorted(
        (read_record(kind, p.stem) for p in folder(kind).glob("*.json")),
        key=lambda record: (record["created_at"], record["id"]),
        reverse=True,
    )
