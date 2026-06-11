from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from orthoplan.mesh_workspace import default_mesh_workspace
from orthoplan.model.assets import CaseRecord, CaseRecordKind, redact_reference

MAX_RECORD_BYTES = 250 * 1024 * 1024


def register_case_record(
    source_path: str | Path,
    *,
    workspace: str | Path | None = None,
    kind: CaseRecordKind = "document",
    modality: str | None = None,
    content_type: str | None = None,
    max_bytes: int = MAX_RECORD_BYTES,
) -> CaseRecord:
    """Copy a non-STL case record into local storage and return redacted metadata."""

    source = Path(source_path)
    size = source.stat().st_size
    if size > max_bytes:
        raise ValueError(f"record file is too large to store safely ({size} bytes)")
    raw = source.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    record_id = sha256[:16]
    safe_name = redact_reference(str(source)) or "record"
    suffix = source.suffix.lower()

    root = Path(workspace) if workspace else default_mesh_workspace()
    record_dir = root / "records"
    record_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{record_id}{suffix}" if suffix else record_id
    shutil.copy2(source, record_dir / filename)

    return CaseRecord(
        id=record_id,
        kind=kind,
        modality=modality,
        filename=safe_name,
        content_type=content_type,
        size_bytes=size,
        sha256=sha256,
        local_reference=f"records/{filename}",
    )
