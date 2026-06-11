from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from orthoplan.mesh_workspace import register_stl_mesh
from orthoplan.server import Handler

ASCII_STL = """solid tooth
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid tooth
"""


@pytest.fixture()
def server() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _get(port: int, path: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _post(
    port: int,
    body: bytes,
    headers: dict[str, str] | None = None,
    path: str = "/api/evaluate",
) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", path, body=body, headers=headers or {})
    resp = conn.getresponse()
    status = resp.status
    payload = json.loads(resp.read() or b"{}")
    conn.close()
    return status, payload


def test_serves_index(server: int) -> None:
    status, body = _get(server, "/")
    assert status == 200
    assert b"OpenSource Ortho" in body


def test_path_traversal_is_blocked(server: int) -> None:
    status, _ = _get(server, "/../orthoplan/api.py")
    assert status == 404
    status, _ = _get(server, "/%2e%2e/orthoplan/server.py")
    assert status == 404


def test_valid_evaluate_returns_findings(server: int) -> None:
    plan = {
        "id": "p",
        "stages": [
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.5}]}
        ],
    }
    status, payload = _post(server, json.dumps(plan).encode(), {"Content-Type": "application/json"})
    assert status == 200
    assert payload["ok"] is True
    assert any("linear cap" in f["title"] for f in payload["findings"])


def test_ai_connector_catalog_is_served(server: int) -> None:
    status, body = _get(server, "/api/ai/connectors")
    payload = json.loads(body)

    assert status == 200
    assert payload["ok"] is True
    assert any(connector["kind"] == "local" for connector in payload["connectors"])


def test_local_chat_endpoint_returns_session(server: int) -> None:
    plan = {"id": "chat", "stages": [
        {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]}]}
    status, payload = _post(
        server,
        json.dumps({"plan": plan, "message": "What can this tell me?", "provider": "local"}).encode(),
        {"Content-Type": "application/json"}, path="/api/chat")

    assert status == 200 and payload["ok"] is True
    assert payload["session"]["connector"]["kind"] == "local"
    assert payload["session"]["messages"][1]["role"] == "assistant"


def test_generate_plan_endpoint_returns_staging(server: int) -> None:
    plan = {
        "id": "gen",
        "scans": [{"asset": {"id": "s1", "format": "stl", "units": "mm",
                             "vertex_count": 0, "face_count": 0}}],
        "stages": [
            {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "21"}, "translate_x_mm": 1.0}]}
        ],
    }
    status, payload = _post(
        server,
        json.dumps({"plan": plan}).encode(),
        {"Content-Type": "application/json"},
        path="/api/generate-plan",
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["source"] == "authored"
    assert payload["correctness"]["verdict"] == "CONSISTENT"
    assert payload["stage_count"] >= 4


def test_plan_version_save_and_list_roundtrip(server: int, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORTHOPLAN_CASE_STORE", str(tmp_path / "cases.json"))
    plan = {"id": "case-srv", "title": "Server case", "stages": [
        {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]}]}
    status, saved = _post(server, json.dumps({"plan": plan, "note": "v1"}).encode(),
                          {"Content-Type": "application/json"}, path="/api/plan/version")
    assert status == 200 and saved["ok"] is True and saved["version"]["version_id"] == "v0001"
    assert any(c["case_id"] == "case-srv" for c in json.loads(_get(server, "/api/cases")[1])["cases"])
    versions = json.loads(_get(server, "/api/cases/case-srv")[1])
    assert versions["ok"] is True and versions["versions"][0]["snapshot"]["id"] == "case-srv"


_CHAT_PLAN = {
    "id": "chat",
    "stages": [
        {"index": 0, "deltas": [{"tooth": {"system": "FDI", "value": "11"}, "translate_x_mm": 0.2}]}
    ],
}


def test_live_chat_endpoint_uses_injected_provider(server: int, monkeypatch) -> None:
    # The server runs in-process, so monkeypatching the provider factory reaches
    # the request handler thread. This guards the live external-connector path
    # end-to-end without contacting a real model.
    import orthoplan.ai_chat as ai_chat
    from orthoplan.evaluation.providers.base import ModelResponse

    class _FakeProvider:
        name = "openai"

        def complete(self, request):  # noqa: ANN001 - test stub
            assert "licensed dental professional" in request.system
            return ModelResponse(text="Mock external educational answer.", model="mock", provider="openai")

    monkeypatch.setattr(ai_chat, "build_chat_provider", lambda *a, **k: _FakeProvider())

    body = json.dumps(
        {
            "plan": _CHAT_PLAN,
            "message": "Explain the timeline",
            "provider": "openai",
            "api_key": "sk-secret-server-test",
            "share_acknowledged": True,
        }
    ).encode()
    status, payload = _post(server, body, {"Content-Type": "application/json"}, path="/api/chat")

    assert status == 200
    assert payload["ok"] is True
    assert payload["session"]["connector"]["kind"] == "openai"
    assert payload["session"]["messages"][1]["content"] == "Mock external educational answer."
    # The browser-supplied key must never be echoed back by the server.
    assert "sk-secret-server-test" not in json.dumps(payload)


def test_external_chat_without_consent_is_rejected(server: int) -> None:
    body = json.dumps(
        {
            "plan": _CHAT_PLAN,
            "message": "Explain the timeline",
            "provider": "openai",
            "api_key": "sk-secret-server-test",
        }
    ).encode()
    status, payload = _post(server, body, {"Content-Type": "application/json"}, path="/api/chat")

    assert status == 200
    assert payload["ok"] is False
    assert "off this machine" in payload["errors"][0]


def test_demo_crown_meshes_are_served(server: int) -> None:
    # The Guided demo loads these bundled crowns over the static path; they must
    # ship and serve as binary STL.
    for kind in ("incisor", "canine", "premolar", "molar"):
        status, body = _get(server, f"/demo-meshes/{kind}.stl")
        assert status == 200, kind
        assert b"OpenSource Ortho" in body[:80]
        assert len(body) > 1000


def test_canonical_orthocad_scans_are_served(server: int) -> None:
    for arch in ("upper", "lower"):
        status, body = _get(server, f"/example-scans/canonical-orthocad-001/sample-test-case-{arch}.stl")
        assert status == 200, arch
        assert len(body) > 10_000_000


def test_invalid_json_is_400(server: int) -> None:
    status, payload = _post(server, b"not json", {"Content-Type": "application/json"})
    assert status == 400
    assert payload["ok"] is False


def test_empty_body_is_400(server: int) -> None:
    status, payload = _post(server, b"")
    assert status == 400
    assert payload["ok"] is False


def test_malformed_content_length_does_not_crash(server: int) -> None:
    # A bad Content-Length must yield a clean 400, not a dropped connection.
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.putrequest("POST", "/api/evaluate")
    conn.putheader("Content-Length", "not-a-number")
    conn.endheaders()
    conn.send(b"{}")
    resp = conn.getresponse()
    assert resp.status == 400
    conn.close()


def test_oversized_body_is_413(server: int) -> None:
    # Declare a length over the cap without sending the bytes; the server must
    # reject on the declared length before reading.
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.putrequest("POST", "/api/evaluate")
    conn.putheader("Content-Length", str(6 * 1024 * 1024))
    conn.endheaders()
    resp = conn.getresponse()
    assert resp.status == 413
    conn.close()


def test_unknown_post_endpoint_is_404(server: int) -> None:
    conn = HTTPConnection("127.0.0.1", server, timeout=5)
    conn.request("POST", "/api/other", body=b"{}", headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_serves_registered_mesh_by_asset_id(server: int, tmp_path, monkeypatch) -> None:
    source = tmp_path / "tooth.stl"
    source.write_text(ASCII_STL, encoding="utf-8")
    workspace = tmp_path / "workspace"
    asset = register_stl_mesh(source, workspace=workspace)
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(workspace))

    status, body = _get(server, f"/api/mesh/{asset.id}")

    assert status == 200
    assert body == ASCII_STL.encode()


def test_mesh_endpoint_blocks_unknown_asset(server: int, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORTHOPLAN_MESH_WORKSPACE", str(tmp_path))

    status, _ = _get(server, "/api/mesh/../secret")

    assert status == 404
