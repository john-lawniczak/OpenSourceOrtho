# AI Chat and MCP Connector Plan

OpenSource Ortho treats AI chat as a scoped advisory layer. It can explain a
plan, findings, data gaps, and timeline, but it must not diagnose, approve
treatment, prescribe aligners, or replace review by a licensed dental
professional.

## Product Direction

- Keep the local deterministic engine as the source of truth for findings.
- Add AI as a conversational explanation layer over a selected context package.
- Support connectors for local helpers, OpenAI, Claude Code, MCP-compatible
hosts, Odysseus, and open-source local models.
- Require explicit configuration before external connectors receive plan data.
- Keep raw API keys session-only unless/until a secure secrets store exists.
- Prefer OAuth or MCP permission handshakes for future account linking, where a
  user grants a trusted agent scoped access to app tools instead of pasting a
  long-lived key into the app.
- Record the connector, model metadata, context scope, plan hash, and messages
for auditability.

## Data Model

Chat orchestration lives in `orthoplan/ai_chat.py`; connector configuration and
live provider construction live in `orthoplan/ai_connectors.py`.

- `AIConnector`: provider metadata such as kind, label, model, endpoint, whether
  it is enabled, and whether it shares patient-derived data.
- `AIContextScope`: controls what the model can see. The default `summary` scope
  includes findings, data gaps, timeline, and clinical controls. `clinical`
  includes mesh metadata. `full_plan` includes the full immutable plan snapshot.
- `ChatMessage`: one user or assistant message with timestamp.
- `ChatSession`: auditable session record containing plan id, plan hash,
  connector, context scope, and messages.

The UI exposes connector, model preference, context scope, session-only API key
entry, and an agent/MCP endpoint field. The API key is read from the DOM only at
send time, is transmitted solely to the selected connector, and is never stored
in app state, `localStorage`, plans, case snapshots, reports, or docs.

## Current Endpoints

- `GET /api/ai/connectors`: returns the connector catalog.
- `POST /api/chat`: answers with the local educational helper by default; when a
  non-local `provider` is selected it performs a live completion through that
  connector (see Live External Connectors below).

## Live External Connectors

`POST /api/chat` accepts `provider`, `model`, `context_scope`, `api_key`,
`endpoint`, and `share_acknowledged`. For any non-local provider the server:

1. Requires `share_acknowledged: true` (egress consent). Without it the request
   is rejected before any external call - scoped plan context never leaves the
   machine by accident.
2. Builds a live provider via `ai_connectors.build_chat_provider`:
   - `openai` - `OpenAIProvider` with the request-supplied key.
   - `claude-code` - `ClaudeCodeProvider` (local `claude` CLI, no key).
   - `mcp` / `odysseus` / `open-source` - `OpenAIProvider` pointed at the
     supplied OpenAI-compatible `endpoint` (key optional).
3. Sends the safety system prompt plus the selected context scope and returns the
   model's text. Provider/credential failures are returned as `ok:false` data,
   never as a server traceback.

The API key is never echoed back in the response or stored in the `ChatSession`.
The dev server binds to `127.0.0.1`, so keys cross only local loopback.

## Account Linking Direction

Short term:

- Let advanced users choose a connector/model and paste a key for the current
  browser session only.
- Do not persist secrets server-side in the local dev server.
- Continue to block external calls unless a configured provider gateway exists.

Long term:

- Add OAuth-style account linking for hosted providers.
- Add an MCP server that exposes read-only, scoped tools to approved local or
  remote agents.
- Require per-session consent for sensitive scopes such as full plan snapshots,
  mesh metadata, or future patient identifiers.
- Record the permission grant, connector, model, context hash, and transcript in
  the case audit trail.

## Next Implementation Steps

1. Persist `ChatSession` records into the case/version store beside immutable
   plan snapshots.
2. Add an MCP server package exposing read-only tools such as `get_plan_summary`,
   `get_findings`, `get_data_gaps`, `get_timeline`, and `get_plan_snapshot`.
3. Add a redaction layer for patient identifiers before any non-local connector
   (the egress consent gate is in place; redaction is the next safety layer).
4. Move from pasted keys to OAuth / MCP permission handshakes for account
   linking, replacing per-request key transmission.

Done: live provider adapters for OpenAI, Claude Code, and OpenAI-compatible
endpoints (MCP / Odysseus / open-source) are wired through `/api/chat`, gated on
per-request egress consent.
