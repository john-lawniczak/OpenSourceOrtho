"""Local development server wiring the static UI to the Python engine.

Serves the ``ui/`` directory and exposes ``POST /api/evaluate`` backed by
``orthoplan.api.evaluate_plan_payload``. This is the bridge that lets the
browser UI consume the canonical engine instead of reimplementing it.

It is a localhost development tool, not a production server. It binds to
127.0.0.1 by default, caps request bodies, and refuses path traversal.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from orthoplan.ai_chat import answer_chat_payload, connector_catalog
from orthoplan.api import evaluate_plan_payload, print_package_payload
from orthoplan.case_api import (
    case_versions_payload,
    list_cases_payload,
    save_plan_version_payload,
)
from orthoplan.cases import default_case_store
from orthoplan.generation import generate_plan_payload
from orthoplan.io.stl_import import MAX_STL_BYTES
from orthoplan.mesh_workspace import default_mesh_workspace, register_stl_mesh, resolve_mesh_path
from orthoplan.model.assets import MeshProvenance, redact_reference
from orthoplan.occlusion.proximity_api import proximity_payload
from orthoplan.record_workspace import MAX_RECORD_BYTES, register_case_record
from orthoplan.segmentation_api import segment_payload

UI_DIR = Path(__file__).resolve().parents[1] / "ui"
MAX_BODY_BYTES = 5 * 1024 * 1024

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".stl": "model/stl",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "OrthoPlanDev/1.0"
    # Avoid a worker thread hanging on a client that declares a body but never sends it.
    timeout = 30

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _resolve_static(self, url_path: str) -> Path | None:
        relative = url_path.lstrip("/") or "index.html"
        candidate = (UI_DIR / relative).resolve()
        if not candidate.is_relative_to(UI_DIR) or not candidate.is_file():
            return None
        return candidate

    def _mesh_workspace(self) -> Path:
        raw = os.environ.get("ORTHOPLAN_MESH_WORKSPACE")
        return Path(raw) if raw else default_mesh_workspace()

    def _case_store(self) -> Path:
        raw = os.environ.get("ORTHOPLAN_CASE_STORE")
        return Path(raw) if raw else default_case_store()

    def _content_length(self) -> int | None:
        """Parsed Content-Length, or None if the header is missing/malformed."""
        raw = self.headers.get("Content-Length")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        try:
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/mesh/"):
                mesh_asset_id = urllib.parse.unquote(path.removeprefix("/api/mesh/"))
                target = resolve_mesh_path(mesh_asset_id, workspace=self._mesh_workspace())
                if target is None:
                    self._send_json(404, {"ok": False, "errors": ["mesh asset not found"]})
                    return
                body = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", _CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/ai/connectors":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "connectors": [connector.model_dump(mode="json") for connector in connector_catalog()],
                    },
                )
                return
            if path == "/api/cases":
                self._send_json(200, list_cases_payload(store_path=self._case_store()))
                return
            if path.startswith("/api/cases/"):
                case_id = urllib.parse.unquote(path.removeprefix("/api/cases/"))
                self._send_json(200, case_versions_payload(case_id, store_path=self._case_store()))
                return
            target = self._resolve_static(path)
            if target is None:
                self._send_json(404, {"ok": False, "errors": ["not found"]})
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:  # noqa: BLE001 - never leak a traceback / drop the connection
            self._send_json(500, {"ok": False, "errors": ["internal server error"]})

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        try:
            path = self.path.split("?", 1)[0]
            if path == "/api/upload/stl":
                _handle_stl_upload(self)
                return
            if path == "/api/upload/record":
                _handle_case_record_upload(self)
                return
            if path not in {
                "/api/evaluate",
                "/api/chat",
                "/api/generate-plan",
                "/api/plan/version",
                "/api/print-package",
                "/api/segment",
                "/api/occlusion",
            }:
                self._send_json(404, {"ok": False, "errors": ["unknown endpoint"]})
                return
            length = self._content_length()
            if length is None or length <= 0:
                self._send_json(400, {"ok": False, "errors": ["missing or invalid Content-Length"]})
                return
            if length > MAX_BODY_BYTES:
                self._send_json(413, {"ok": False, "errors": ["request body too large"]})
                return
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "errors": ["invalid JSON body"]})
                return
            if not isinstance(payload, dict):
                self._send_json(400, {"ok": False, "errors": ["plan payload must be an object"]})
                return
            if path == "/api/chat":
                self._send_json(200, answer_chat_payload(payload))
            elif path == "/api/generate-plan":
                self._send_json(200, generate_plan_payload(payload))
            elif path == "/api/plan/version":
                self._send_json(200, save_plan_version_payload(payload, store_path=self._case_store()))
            elif path == "/api/print-package":
                self._send_json(
                    200, print_package_payload(payload, workspace=self._mesh_workspace())
                )
            elif path == "/api/segment":
                self._send_json(
                    200,
                    segment_payload(payload, ui_dir=UI_DIR, workspace=self._mesh_workspace()),
                )
            elif path == "/api/occlusion":
                self._send_json(
                    200,
                    proximity_payload(payload, ui_dir=UI_DIR, workspace=self._mesh_workspace()),
                )
            else:
                self._send_json(200, evaluate_plan_payload(payload))
        except Exception:  # noqa: BLE001 - never leak a traceback / drop the connection
            self._send_json(500, {"ok": False, "errors": ["internal server error"]})

    def log_message(self, *args: object) -> None:  # silence default stderr logging
        return


def _handle_stl_upload(handler: Handler) -> None:
    length = handler._content_length()
    if length is None or length <= 0:
        handler._send_json(400, {"ok": False, "errors": ["missing or invalid Content-Length"]})
        return
    if length > MAX_STL_BYTES:
        handler._send_json(413, {"ok": False, "errors": ["STL upload too large"]})
        return

    filename = redact_reference(
        urllib.parse.unquote(handler.headers.get("X-Filename", "uploaded.stl"))
    ) or "uploaded.stl"
    if not filename.lower().endswith(".stl"):
        handler._send_json(400, {"ok": False, "errors": ["only .stl uploads are supported"]})
        return

    raw = handler.rfile.read(length)
    with tempfile.TemporaryDirectory(prefix="orthoplan-upload-") as tmp:
        temp_path = Path(tmp) / filename
        temp_path.write_bytes(raw)
        try:
            asset = register_stl_mesh(
                temp_path,
                workspace=handler._mesh_workspace(),
                provenance=MeshProvenance.PATIENT_DERIVED,
            )
        except Exception as exc:  # noqa: BLE001 - return validation errors as data
            handler._send_json(400, {"ok": False, "errors": [f"could not register STL: {exc}"]})
            return

    handler._send_json(
        200,
        {
            "ok": True,
            "asset": asset.model_dump(mode="json"),
            "url": f"/api/mesh/{asset.id}",
        },
    )


def _handle_case_record_upload(handler: Handler) -> None:
    length = handler._content_length()
    if length is None or length <= 0:
        handler._send_json(400, {"ok": False, "errors": ["missing or invalid Content-Length"]})
        return
    if length > MAX_RECORD_BYTES:
        handler._send_json(413, {"ok": False, "errors": ["case record upload too large"]})
        return

    kind = handler.headers.get("X-Record-Kind", "document").strip().lower()
    if kind not in {"cbct", "dicom", "photo", "radiograph", "document"}:
        handler._send_json(400, {"ok": False, "errors": ["unsupported case record kind"]})
        return

    filename = redact_reference(
        urllib.parse.unquote(handler.headers.get("X-Filename", "record"))
    ) or "record"
    modality = handler.headers.get("X-Modality")
    content_type = handler.headers.get("Content-Type")

    raw = handler.rfile.read(length)
    with tempfile.TemporaryDirectory(prefix="orthoplan-record-") as tmp:
        temp_path = Path(tmp) / filename
        temp_path.write_bytes(raw)
        try:
            record = register_case_record(
                temp_path,
                workspace=handler._mesh_workspace(),
                kind=kind,  # type: ignore[arg-type]
                modality=modality,
                content_type=content_type,
            )
        except Exception as exc:  # noqa: BLE001 - return validation errors as data
            handler._send_json(400, {"ok": False, "errors": [f"could not register record: {exc}"]})
            return

    handler._send_json(200, {"ok": True, "record": record.model_dump(mode="json")})


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"OpenSource Ortho dev server on http://{host}:{port} (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        httpd.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenSource Ortho local UI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
