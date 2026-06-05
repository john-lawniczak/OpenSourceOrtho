# OpenAI Agents

This document tracks how OpenSource Ortho should use OpenAI-compatible agentic model providers.

## Role

OpenAI-backed agents are advisory reviewers only. They may summarize plan data, identify configured-rule findings already present in the report, and suggest follow-up questions under declared data limitations.

They must not:

- approve a treatment plan
- diagnose a patient
- invent movement thresholds
- infer unavailable anatomy
- override deterministic rule findings
- suppress data gaps
- emit `mechanics` findings (forbidden for model provenance in Phase 1; deterministic rules own mechanics)

Model output is untrusted. It must pass `lint_finding()` (the single safety gate) and is
quarantined on failure via `quarantine_findings()` rather than crashing the pipeline. Verdict
language is scanned across every text field, not just the title and message.

## Advisory Pipeline

The model advisory layer lives in `orthoplan/evaluation/advisory.py` and is
**opt-in** - it runs only when a caller passes a provider (e.g. `orthoplan advise`
or `request_advisory(plan, provider)`). The default evaluation path
(`api.evaluate_plan`) never calls a model.

Flow: `build_advisory_request(plan)` injects the safety boundary, the declared
`DataAvailability`, the configured `MovementCaps`, and a strict JSON output
schema. The provider's text is parsed into `AdvisoryResponse` (markdown fences
tolerated), each item becomes a `Finding(provenance=MODEL)`, and the batch goes
through `quarantine_findings` - the same `lint_finding` gate as deterministic
findings. Unparseable output, verdict language, model-sourced `mechanics`
findings, and warnings missing a data gap or follow-up question are rejected as
data (`AdvisoryResult.parse_error` / `.rejected`), never raised. Accepted
findings always render with the `[ADVISORY - unverified]` prefix.

## First Adapter

The first remote model adapter is `OpenAIProvider` in `orthoplan/evaluation/providers/openai_provider.py`.

The adapter is intentionally narrow:

- accepts a provider-neutral `ModelRequest`
- returns provider-neutral `ModelResponse`
- does not own deterministic policy
- does not bypass `lint_finding()`
- converts SDK/CLI execution failures into `RuntimeError` so `orthoplan advise`
  exits cleanly instead of surfacing provider tracebacks
- accepts an injected `api_key` and `base_url`, so the same adapter drives the
  official OpenAI API and any OpenAI-compatible host (MCP / Odysseus /
  open-source local model servers). An explicit key wins over `OPENAI_API_KEY`.

Default model: `gpt-5.5`, based on current OpenAI model guidance checked during
the initial scaffold on 2026-06-03 and rechecked during the 2026-06-04
post-implementation audit.

## Chat Connector Use

Beyond the `advise` pipeline, the adapter also backs the live AI chat layer. The
chat path (`orthoplan/ai_chat.py` + `orthoplan/ai_connectors.py`) builds an
`OpenAIProvider` per request from a browser-supplied key/endpoint, but only after
an explicit egress-consent flag (`share_acknowledged`) is set. The key is never
persisted nor echoed back. See [AI_CHAT_MCP.md](AI_CHAT_MCP.md) for the endpoint
contract and the connector kinds.

## Commit Status

When provider behavior changes, update this file in the same commit and summarize the change in your pull request description.

## Maintainability Agent Guidance

OpenAI agents working in this repository should preserve long-term composability.

Before proposing or applying code changes, check:

- whether the change belongs in `model`, `io`, `planning`, `evaluation`, or `viz`
- whether provider-specific SDK code is isolated behind a provider adapter
- whether deterministic rules remain separate from model-generated advisory text
- whether new UI-facing code consumes explicit frame contracts instead of recalculating movement
- whether files, functions, or classes are growing past the thresholds in [MAINTAINABILITY.md](MAINTAINABILITY.md)

Prefer small, typed modules and focused tests. Do not create large multipurpose files that mix IO, planning, evaluation, and rendering concerns.
