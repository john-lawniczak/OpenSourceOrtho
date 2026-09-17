"""Binary upload endpoints for the local dev server.

Split out of ``server`` by responsibility: routing, static files, and JSON
payload dispatch stay there; the two endpoints that accept raw bytes live here.
Both write the body to a temporary file, hand it to the workspace registrar,
and return metadata - the bytes themselves are never held in the response.

Handlers never raise: a bad upload comes back as a 400 with the reason.
"""

from __future__ import annotations

import tempfile
import urllib.parse
from pathlib import Path
from typing import Protocol

from orthoplan.io.mesh_formats import SCAN_SUFFIXES, SUPPORTED_FORMATS_TEXT
from orthoplan.io.mesh_import import MAX_SCAN_BYTES
from orthoplan.mesh_workspace import register_scan_mesh
from orthoplan.model.assets import MeshProvenance, redact_reference
from orthoplan.record_workspace import MAX_RECORD_BYTES, register_case_record

RECORD_KINDS = {"cbct", "dicom", "photo", "radiograph", "document"}


class UploadHandler(Protocol):
    """The slice of the server request handler these endpoints rely on."""

    headers: object
    rfile: object

    def _send_json(self, status: int, payload: dict) -> None: ...
    def _content_length(self) -> int | None: ...
    def _mesh_workspace(self) -> Path: ...


def handle_scan_upload(handler: UploadHandler) -> None:
    """Register an uploaded scan in any supported format."""

    length = _body_length(handler, MAX_SCAN_BYTES, "scan upload too large")
    if length is None:
        return

    filename = _filename(handler, "uploaded.stl")
    if Path(filename).suffix.lower() not in SCAN_SUFFIXES:
        handler._send_json(
            400,
            {
                "ok": False,
                "errors": [f"unsupported scan file type; supported: {SUPPORTED_FORMATS_TEXT}"],
            },
        )
        return

    with _received(handler, length, filename, "orthoplan-upload-") as temp_path:
        try:
            asset = register_scan_mesh(
                temp_path,
                workspace=handler._mesh_workspace(),
                provenance=MeshProvenance.PATIENT_DERIVED,
            )
        except Exception as exc:  # noqa: BLE001 - return validation errors as data
            handler._send_json(400, {"ok": False, "errors": [f"could not register scan: {exc}"]})
            return

    handler._send_json(
        200,
        {"ok": True, "asset": asset.model_dump(mode="json"), "url": f"/api/mesh/{asset.id}"},
    )


def handle_case_record_upload(handler: UploadHandler) -> None:
    """Register an uploaded case record (CBCT, photo, radiograph, document)."""

    length = _body_length(handler, MAX_RECORD_BYTES, "case record upload too large")
    if length is None:
        return

    kind = handler.headers.get("X-Record-Kind", "document").strip().lower()
    if kind not in RECORD_KINDS:
        handler._send_json(400, {"ok": False, "errors": ["unsupported case record kind"]})
        return

    filename = _filename(handler, "record")
    with _received(handler, length, filename, "orthoplan-record-") as temp_path:
        try:
            record = register_case_record(
                temp_path,
                workspace=handler._mesh_workspace(),
                kind=kind,  # type: ignore[arg-type]
                modality=handler.headers.get("X-Modality"),
                content_type=handler.headers.get("Content-Type"),
            )
        except Exception as exc:  # noqa: BLE001 - return validation errors as data
            handler._send_json(400, {"ok": False, "errors": [f"could not register record: {exc}"]})
            return

    handler._send_json(200, {"ok": True, "record": record.model_dump(mode="json")})


def _body_length(handler: UploadHandler, limit: int, too_large: str) -> int | None:
    """Validated Content-Length, or ``None`` after sending the error response."""

    length = handler._content_length()
    if length is None or length <= 0:
        handler._send_json(400, {"ok": False, "errors": ["missing or invalid Content-Length"]})
        return None
    if length > limit:
        handler._send_json(413, {"ok": False, "errors": [too_large]})
        return None
    return length


def _filename(handler: UploadHandler, fallback: str) -> str:
    """The client's filename, reduced to a non-identifying basename."""

    raw = urllib.parse.unquote(handler.headers.get("X-Filename", fallback))
    return redact_reference(raw) or fallback


class _received:
    """Body bytes on disk under a temporary directory, removed on exit."""

    def __init__(self, handler: UploadHandler, length: int, filename: str, prefix: str) -> None:
        self._handler = handler
        self._length = length
        self._filename = filename
        self._tmp = tempfile.TemporaryDirectory(prefix=prefix)

    def __enter__(self) -> Path:
        path = Path(self._tmp.name) / self._filename
        path.write_bytes(self._handler.rfile.read(self._length))
        return path

    def __exit__(self, *exc_info: object) -> None:
        self._tmp.cleanup()
