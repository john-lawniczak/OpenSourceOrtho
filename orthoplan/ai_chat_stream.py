from __future__ import annotations

import json
import textwrap
from collections.abc import Iterable
from typing import Any

from orthoplan.ai_chat import answer_chat_payload
from orthoplan.evaluation.providers.base import ModelProvider


def chat_stream_events(
    payload: dict[str, Any],
    *,
    provider: ModelProvider | None = None,
) -> Iterable[dict[str, Any]]:
    """Yield SSE-friendly chat events with a final canonical chat response."""

    result = answer_chat_payload(payload, provider=provider)
    if result.get("ok") is False:
        yield {"event": "error", "data": {"errors": result.get("errors", [])}}
        return

    session = result["session"]
    connector = session["connector"]
    assistant = next(
        (
            item
            for item in reversed(session["messages"])
            if item.get("role") == "assistant"
        ),
        {"content": ""},
    )
    yield {
        "event": "meta",
        "data": {
            "connector": connector,
            "context_scope": session["context_scope"],
            "session_id": session["session_id"],
        },
    }
    for chunk in _answer_chunks(assistant.get("content", "")):
        yield {"event": "delta", "data": {"text": chunk}}
    yield {"event": "done", "data": result}


def format_sse_event(event: str, data: dict[str, Any]) -> bytes:
    body = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


def send_chat_stream(handler: Any, payload: dict[str, Any]) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    for item in chat_stream_events(payload):
        handler.wfile.write(format_sse_event(item["event"], item["data"]))
        handler.wfile.flush()


def _answer_chunks(text: str) -> Iterable[str]:
    for chunk in textwrap.wrap(text, width=48, break_long_words=False, replace_whitespace=False):
        yield chunk + (" " if chunk and not chunk.endswith((" ", "\n")) else "")
