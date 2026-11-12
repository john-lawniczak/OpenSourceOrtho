# OpenAI Agents

This document tracks how OpenSource Ortho should use OpenAI-compatible agentic model providers.

## Role

OpenAI-backed agents are advisory reviewers only. They may summarize plan data, identify configured-rule findings already present in the report, and suggest follow-up questions under declared data limitations.

They must not:

- approve a treatment plan
- diagnose a patient
- produce or claim to produce a complete treatment plan
- authorize printing, wearing, or physically applying any output
- invent movement thresholds
- infer unavailable anatomy
- override deterministic rule findings
- suppress data gaps
- emit `mechanics` findings (forbidden for model provenance in Phase 1; deterministic rules own mechanics)

Model output is untrusted. It must pass `lint_finding()` (the single safety gate) and is
quarantined on failure via `quarantine_findings()` rather than crashing the pipeline. Verdict
language is scanned across every text field, not just the title and message.
Any generated explanation must preserve that physical use is the user's own
responsibility and risk.

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
- accepts an injected `api_key` and optional Responses-compatible `base_url`.
  An explicit key wins over `OPENAI_API_KEY`.

Default OpenAI model: `gpt-6.1-sol`. The catalog also offers Astra, Terra, Luna,
and a custom model ID. Checked against the [official OpenAI model catalog](https://developers.openai.com/api/docs/models)
on 2026-11-04.

OpenAI-compatible Chat Completions hosts use the separate `CompatibleProvider`
adapter, not the Responses endpoint. DeepSeek defaults to `deepseek-flash` at
`https://api.deepseek.com`; GLM defaults to `glm-5.3` at
`https://api.z.ai/api/paas/v4/`. Model IDs and endpoints were checked against the
[DeepSeek quickstart](https://api-docs.deepseek.com/) and
[Z.ai quickstart](https://docs.z.ai/guides/overview/quick-start) on 2026-11-04.
Both accept custom model IDs. Local/open-weight and compatible hosts accept the
server's exact model ID and base URL (including `/v1` when required). The legacy
`mcp` connector ID remains for compatibility, but the UI calls it an
OpenAI-compatible host: this adapter does not implement MCP tool discovery.

Claude Code uses its installed CLI authentication and default model unless a
model or CLI alias is selected. The selected model is now passed to `--model`;
the UI labels it **Claude Code (local CLI)** and explains that it takes no key.
**Claude API (Anthropic)** is a separate `anthropic` connector with a visible
API-key field. `AnthropicProvider` uses the Python SDK's Messages API with the
system prompt separate from the user/context message, a 4,096-token output cap,
120-second timeout, and no retries or tools. It accepts only finished text
responses; incomplete answers and SDK errors produce sanitized failures.
All responses still pass the existing finding lint gate. Defaults are Sonnet 5.5,
with Opus 5.5, Haiku 5.5 and custom IDs available. IDs and protocol were checked
against [Anthropic's model catalog](https://platform.claude.com/docs/en/models/overview)
and [Messages API](https://platform.claude.com/docs/en/api/python/messages/create)
on 2026-11-12. Model access depends on the supplied account.

The `providers` extra installs both OpenAI and Anthropic SDKs. The launcher now
installs `.[dev,providers]` and checks SDK imports even when its install stamp
exists. Manual web setup includes that extra too. OpenAI continues to use the
Responses API, as in the [official Python quickstart](https://developers.openai.com/api/docs/quickstart).

## Chat Connector Use

Beyond the `advise` pipeline, the adapter also backs the live AI chat layer. The
chat path (`orthoplan/ai_chat.py` + `orthoplan/ai_connectors.py`) builds an
provider adapter per request from a browser-supplied key/endpoint, but only after
an explicit egress-consent flag (`share_acknowledged`) is set. The key is never
persisted nor echoed back. See [AI_CHAT_MCP.md](AI_CHAT_MCP.md) for the endpoint
contract and the connector kinds.

The browser’s **top-bar gear → Settings** dialog contains separate provider and
model selectors, a session-only API key, and endpoint controls for compatible
hosts. Custom IDs are available when a connector supports them. Provider/model
choices come from the connector catalog. The default local helper needs no key.
Changing providers clears the key, endpoint, and sharing consent to prevent
accidental credential reuse. Settings close with Done or Escape; configuration
stays available without occupying the conversation area. Nothing is sent merely
by configuring a connector. Keys are never written to browser storage or plans.

External requests still require explicit consent to share the selected case context
and conversation. Chat uses `context_scope = full_plan`. Generate Plan reuses
this configuration for its optional advisory review; both paths retain the
server-side lint gate.

The conversation, unsent prompt, selected provider/models, and panel layout are
saved in same-origin `sessionStorage` for navigation and reloads in the same tab.
This is a tab session, not a permanent case record or cross-tab sync. Keys,
endpoints, consent, and plan snapshots are excluded by an explicit allowlist;
full-page navigation/reload requires fresh credentials and sharing consent.
The UI discloses storage failures and reminds users that each new request uses
the selected context (restoring a transcript does not restore its old plan).

The latest 16 successful messages are sent as follow-up context. Failed turns
are excluded and their prompts remain available in the composer or **Reuse
prompt**. Missing credentials open Settings before clearing the draft. New chat
clears the thread, draft, and server session ID. Pending requests interrupted by
navigation recover as failed turns with their prompts retained; no request is
automatically resent. The browser aborts its fetch, but this does not guarantee
cancellation of an external provider call already running on the server.
Stream deltas update an existing assistant turn using text nodes, preserving
line breaks and never interpreting model HTML. The server only streams answers
after its existing lint gate.

## Plan Generation Orchestration

Beyond `advise` and chat, the model layer also backs the OPTIONAL review step of
plan generation (`orthoplan/generation.py`). The generation pipeline is
deterministic first:

1. review scan inputs, 2. generate cap-respecting staging
(`planning/generate.py`), 3. validate with `run_rules`, 4. a deterministic
correctness review producing a `CONSISTENT` / `ISSUES` / `NOT_APPLICABLE`
verdict, then 5. an optional model advisory review.

The model step reuses the existing `advisory.py` pipeline (`request_advisory`),
so it inherits every guarantee: untrusted output is parsed into a strict schema,
each item becomes a `Finding(provenance=MODEL)`, and the batch passes
`quarantine_findings`/`lint_finding`. The same prohibitions apply - no model
`mechanics` findings, no verdict/approval language, warnings need a data gap and a
follow-up question, accepted findings render with `[ADVISORY - unverified]`.

Optional free-text user **notes** (e.g. "focus on the lateral incisors") are
appended to the review prompt by `build_advisory_request(plan, notes=...)`. Notes
are context for the reviewer only: they never change deterministic staging, never
relax the boundary in the system prompt, and the model's output still passes
`lint_finding()`.

When no external model is connected (the default), notes are still acted on
offline by `evaluation/local_review.py::local_notes_advisory` - a deterministic,
linted educational finding (MODEL provenance, `[ADVISORY - unverified]`) that
reflects the focus back and relates it to the plan's actual movements. It does not
reason freely; it routes the user to a professional.

The model step is opt-in and consent-gated: it runs only when an external
connector is selected AND the egress acknowledgement (`share_acknowledged`) is
set, exactly like the chat connector. The connector is configured in the Plan AI
settings dialog (provider, model, session-only key, endpoint, and sharing consent) - and is reused by Generate Plan. With the local connector or no
consent, the pipeline completes fully offline and the model step is recorded as
`skipped`. The deterministic correctness verdict is never produced or overridden
by a model.

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

### Selected-tooth geometric previews

`POST /api/preview-goal` interprets an explicit change to one reviewed scan tooth.
The request carries `selected_tooth`, `message`, the working plan and the existing
connector settings. External calls require `share_acknowledged`; the selected
tooth's existing target, request text, and structured workspace inventory are
sent to the provider, not scan bytes.
The local helper accepts explicit commands such as `move 0.2 mm right`. Manual
nudges use `adjustment: {x_mm, y_mm}` and do not call an external model.

A provider returns strict JSON containing the same tooth ID, additional scan-local
X/Y translation, and a brief explanation. The gateway rejects other teeth, extra
axes, non-finite values, unconfirmed units, missing reviewed mesh links, fixed
teeth and movement exclusions. Both the requested change and resulting target
are bounded by the editor's ±4 mm per-axis limit; this is not a clinical limit.
Ambiguous requests can return a clarification with zero movement.

Model explanations pass `lint_finding()` before display. Ordinary external chat
answers now pass the same gate before either normal or SSE responses are emitted.
Rejected model text is not echoed in the error response.

The existing deterministic staging optimizer builds the candidate. The browser
then evaluates it through `/api/evaluate`, previews its real segmented crowns,
and requires **Apply change** to replace authored rows. **Discard** leaves the
working plan unchanged; **Undo** restores the previous rows after applying.
In-flight results are rejected when the working plan changes. Model provenance
is retained on applied movement rows. This is geometric intent editing, not
an autonomous treatment recommendation from an uploaded scan.

### Structured workspace context

Full-plan chat includes `workspace`: scan formats, arch, confirmed units, counts,
bounds, quality metadata, per-tooth mesh links and review state, coordinate frame,
and an explicit capability map. The existing full snapshot, deterministic
findings, data gaps and timeline remain available. The browser adds the current
step, view, stage index, selected FDI tooth and sample flag. Tooth-goal parsing
receives the same workspace inventory alongside the selected target.

This is structured application context, not unrestricted access. Raw vertices,
triangles, scan images, CBCT pixels and arbitrary filesystem/application commands
are not exposed. Local references in metadata do not grant file access. The
system prompt distinguishes this metadata from surface inspection and treats
uploaded notes as untrusted data. The chat's “What the assistant can see” disclosure
states these limits. Existing sharing consent and output linting still apply;
only explicit, validated tooth previews can be applied by the user.

### 2026-11-04 post-implementation audit

Single-tooth previews now **append only the additional movement** after the
existing stages. They preserve other teeth's paths, existing timing, controls,
and provenance rather than collapsing the whole plan into final totals and
re-staging it. Additional staging is bounded to 512 stages; unrelated teeth's
control horizons do not enlarge that search. The browser preserves movement
provenance and mesh references when converting the result into editable rows.

Claude Code now runs with `--bare`, no built-in or MCP tools, and
`--no-session-persistence`; plan context is passed on stdin, not exposed in the
process argument list. These controls follow the [official CLI reference](https://code.claude.com/docs/en/cli-reference).
An older CLI that rejects these flags fails closed; there is no unrestricted
fallback. Provider subprocess/HTTP calls use a 120-second timeout, SDK automatic
retries are disabled, and raw SDK/CLI error bodies are not returned to the UI.
OpenAI clients close after each request. Live authenticated provider behavior
still requires release smoke testing; automated provider tests use stubs.

The local server rejects foreign/null Origin POSTs and cross-site browser
requests before dispatching uploads, writes, or provider calls. This is a browser
request boundary, not authentication for exposing the development server on a
network. Generation and sample fixture results are scoped to the originating
workspace; stale responses cannot replace another case or its controls.

### Opt-in provider protocol smoke tests

Offline fault tests cover authentication errors, timeouts, malformed/empty replies,
redaction, client cleanup and the 120-second/no-retry policy. Empty OpenAI Responses
output now fails explicitly, matching compatible-provider behavior.

Live tests send only a synthetic connectivity token, never a plan or scan. They
are disabled by default and may incur provider charges. Configure credentials in
the process environment, then run, for example:

```sh
ORTHOPLAN_LIVE_PROVIDERS=deepseek,glm python -m pytest tests/test_provider_smoke.py -q
```

Use `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GLM_API_KEY`, or
`OPEN_SOURCE_API_KEY`/`OPEN_SOURCE_ENDPOINT`; optional `<PREFIX>_MODEL` selects
an explicit model. Claude Code uses its installed CLI authentication. Each live
test has a 150-second process deadline. A standalone check requires explicit opt-in:
`python -m orthoplan.validation.provider_smoke --live --provider deepseek`.
Failures print only provider and exception type, never upstream response bodies.

Local mesh-model integration now requires an explicit, hash-bound ONNX contract
(`orthoplan/segmentation/model_contract.py`). Feature layout, output shape, arch,
and FDI mapping are checked before a draft can be rendered. Invalid predictions
fail the local fitting job; they are not accepted as reviewed tooth geometry.
See [tool improvement phases](TOOL_IMPROVEMENT_PHASES.md).

### Local endpoint-fit explanations

`/api/motion-review` is a deterministic local helper for two-visit research fits.
It accepts at most 32 regions with FDI labels, fit statuses and finite numeric
metrics. It ignores caller prose and generates educational findings through
`lint_finding()` before returning them. The UI sends only these metadata fields;
raw surfaces, CBCT pixels and filesystem paths are excluded. It does not contact
an external provider or infer tooth identity from a small surface residual.
Explanations prioritize held and weak regions and distinguish a held zero pose
from evidence of no movement. Imported cases receive a fresh local explanation
instead of displaying imported advisory text as newly generated findings.

### OpenAI connection failures

The OpenAI adapter defaults explicitly to `https://api.openai.com/v1` rather than
inheriting an SDK base URL. Request-supplied keys are trimmed and do not inherit
process organization/project IDs; environment-based CLI credentials retain their
scope. Explicit adapter base URLs remain supported. Authentication, access, model,
quota, rate and connection errors use fixed actionable messages without copying
upstream bodies, key fragments or plan data. Failed chat turns link to Connection
settings and retain their prompts. These changes do not validate a user's actual
key; a successful authenticated request is still required.

See [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes).

Browser-supplied OpenAI credentials now explicitly set the bearer header so an
ambient SDK authorization header cannot substitute a different credential.
Organization and project are cleared after construction, which omits those
headers instead of sending empty values. A real SDK serialization test with a
mock HTTP transport verifies the endpoint, bearer value and omitted scope headers;
it uses synthetic credentials and sends no network request. The allowlisted
`invalid_api_key` error code is shown when supplied by OpenAI; other response
bodies remain hidden. Authentication of a user's real key remains unverified
until a real request succeeds. Chat recovery buttons use a spaced, wrapping row.

### Selected case context and compact composer

Chat's **Context** selector separates the current planning workspace from
**USER_ONE scans & saved labels**. Automatic mode follows the sample scan-history
view; the simulated planning demo uses its workspace plan. Returning from a
USER_ONE baseline painting page selects USER_ONE explicitly. The selection
survives same-tab reloads with the conversation, and is visible before sending.

A `case_source: user_one` request in `full_plan` scope builds bounded metadata
from fixed, specimen-checked manifests: baseline/week 7 scans, week 18
records (including H4/H6 when installed), latest hash-validated local annotation
counts and notes, and endpoint-estimate status summaries. No caller-supplied
filesystem path is accepted. Week 18 records now come from the publication-approved
`visits/progress-02/` manifests; these records are no longer marked private.
Other private files remain excluded from public assets;
the selected provider receives these metadata only on Send with sharing consent.
The context omits the unrelated workspace plan and never changes authored data.
USER_ONE chat is read-only; tooth-change previews use the planning workspace.

Raw mesh arrays, label arrays, screenshots, unsaved paint and arbitrary files
remain unavailable to the model. Source notes remain untrusted. Draft numbering,
model damage, unverified progress units, and estimates not regenerated from the
latest painting are explicit limitations. This supplies record awareness, not
visual assessment of contacts or an enamel/space analysis for IPR.

The composer starts as one line, expands on focus, and collapses on blur, Send,
or its Collapse button. Draft text survives collapse and reload. Opening the
chat panel does not automatically expand the composer.

Selected USER_ONE context also supplies `dentition` from the specimen-checked
`treatment-context.json`: contributor-reported wisdom-tooth removal (18/28/38/48),
with extraction dates unknown. This is reported history, not an independent
anatomical finding. Published annotation drafts remain distinct from locally saved
labels and the existing motion estimates.
