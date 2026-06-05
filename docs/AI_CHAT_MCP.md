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

The current implementation lives in `orthoplan/ai_chat.py`.

- `AIConnector`: provider metadata such as kind, label, model, endpoint, whether
  it is enabled, and whether it shares patient-derived data.
- `AIContextScope`: controls what the model can see. The default `summary` scope
  includes findings, data gaps, timeline, and clinical controls. `clinical`
  includes mesh metadata. `full_plan` includes the full immutable plan snapshot.
- `ChatMessage`: one user or assistant message with timestamp.
- `ChatSession`: auditable session record containing plan id, plan hash,
  connector, context scope, and messages.

The UI exposes connector, model preference, context scope, session-only API key
entry, and future agent/MCP endpoint fields. The API key field is a staging UI
only: it is not persisted in plans, case snapshots, reports, or docs.

## Current Endpoints

- `GET /api/ai/connectors`: returns the connector catalog.
- `POST /api/chat`: answers with the local educational helper by default.

External connectors are modeled but disabled in the local server until a user
adds an explicit provider gateway. This prevents accidental plan-context sharing.

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
3. Add provider adapters for configured OpenAI, Claude Code, local open-source
   model endpoints, and Odysseus-compatible endpoints.
4. Add per-session consent controls before full-plan or mesh metadata context is
   shared externally.
5. Add a redaction layer for patient identifiers before any non-local connector.
