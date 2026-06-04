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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from orthoplan.api import evaluate_plan_payload

UI_DIR = Path(__file__).resolve().parents[1] / "ui"
MAX_BODY_BYTES = 5 * 1024 * 1024

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "OrthoPlanDev/1.0"

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

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
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

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.split("?", 1)[0] != "/api/evaluate":
            self._send_json(404, {"ok": False, "errors": ["unknown endpoint"]})
            return
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(413, {"ok": False, "errors": ["request body missing or too large"]})
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
        self._send_json(200, evaluate_plan_payload(payload))

    def log_message(self, *args: object) -> None:  # silence default stderr logging
        return


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
