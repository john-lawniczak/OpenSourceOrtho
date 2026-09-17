"""Local development server wiring the static UI to the Python engine."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from orthoplan.ai_chat import answer_chat_payload, connector_catalog
from orthoplan.ai_chat_stream import send_chat_stream
from orthoplan.api import evaluate_plan_payload, print_package_payload
from orthoplan.case_api import case_versions_payload, list_cases_payload, save_plan_version_payload
from orthoplan.case_review import case_review_payload
from orthoplan.cases import default_case_store
from orthoplan.cbct_workflow import cbct_proposal_payload, cbct_review_payload
from orthoplan.generation import generate_plan_payload
from orthoplan.mesh_workspace import default_mesh_workspace, resolve_mesh_path
from orthoplan.occlusion.proximity_api import proximity_payload
from orthoplan.segmentation_api import segment_payload
from orthoplan.server_uploads import handle_case_record_upload, handle_scan_upload
from orthoplan.setup_compare import compare_setups_payload, live_restage_comparison_payload

UI_DIR = Path(__file__).resolve().parents[1] / "ui"
MAX_BODY_BYTES = 5 * 1024 * 1024

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".stl": "model/stl",
    # Canonical point-cloud storage; served as text so the viewer can read it.
    ".xyz": "text/plain; charset=utf-8",
}

JSON_POST_ENDPOINTS = {
    "/api/evaluate", "/api/chat", "/api/chat/stream", "/api/generate-plan",
    "/api/plan/version", "/api/print-package", "/api/case-review",
    "/api/setup-compare", "/api/cbct/propose-anatomy", "/api/cbct/review-anatomy",
    "/api/segment", "/api/occlusion",
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
            if path in {"/api/upload/scan", "/api/upload/stl"}:
                handle_scan_upload(self)
                return
            if path == "/api/upload/record":
                handle_case_record_upload(self)
                return
            if path not in JSON_POST_ENDPOINTS:
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
            if path == "/api/chat/stream":
                send_chat_stream(self, payload)
                return
            self._send_json(200, _dispatch_json_post(self, path, payload))
        except Exception:  # noqa: BLE001 - never leak a traceback / drop the connection
            self._send_json(500, {"ok": False, "errors": ["internal server error"]})

    def log_message(self, *args: object) -> None:  # silence default stderr logging
        return


def _dispatch_json_post(handler: Handler, path: str, payload: dict) -> dict:
    if path == "/api/chat":
        return answer_chat_payload(payload)
    if path == "/api/generate-plan":
        return generate_plan_payload(payload)
    if path == "/api/plan/version":
        return save_plan_version_payload(payload, store_path=handler._case_store())
    if path == "/api/print-package":
        return print_package_payload(payload, workspace=handler._mesh_workspace())
    if path == "/api/case-review":
        return case_review_payload(payload)
    if path == "/api/setup-compare":
        if payload.get("live_restage"):
            return live_restage_comparison_payload(payload)
        return compare_setups_payload(payload)
    if path == "/api/cbct/propose-anatomy":
        return cbct_proposal_payload(payload)
    if path == "/api/cbct/review-anatomy":
        return cbct_review_payload(payload)
    if path == "/api/segment":
        return segment_payload(payload, ui_dir=UI_DIR, workspace=handler._mesh_workspace())
    if path == "/api/occlusion":
        return proximity_payload(payload, ui_dir=UI_DIR, workspace=handler._mesh_workspace())
    return evaluate_plan_payload(payload, workspace=handler._mesh_workspace())


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
