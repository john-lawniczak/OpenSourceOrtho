# OpenAI Agents

This document tracks how OpenSource Ortho should use OpenAI-compatible agentic model providers.

## Role

OpenAI-backed agents are advisory reviewers only. They may summarize plan data, identify configured-rule findings already present in the report, and suggest clinician questions under declared data limitations.

They must not:

- approve a treatment plan
- diagnose a patient
- invent movement thresholds
- infer unavailable anatomy
- override deterministic rule findings
- suppress data gaps

## First Adapter

The first remote model adapter is `OpenAIProvider` in `orthoplan/evaluation/providers/openai_provider.py`.

The adapter is intentionally narrow:

- accepts a provider-neutral `ModelRequest`
- returns provider-neutral `ModelResponse`
- does not own clinical policy
- does not bypass `lint_finding()`

Default model: `gpt-5.5`, based on current OpenAI model guidance checked during the initial scaffold on 2026-06-03.

## Commit Status

When provider behavior changes, update this file and [Dev_history.md](Dev_history.md) in the same commit.

## Maintainability Agent Guidance

OpenAI agents working in this repository should preserve long-term composability.

Before proposing or applying code changes, check:

- whether the change belongs in `model`, `io`, `planning`, `evaluation`, or `viz`
- whether provider-specific SDK code is isolated behind a provider adapter
- whether deterministic rules remain separate from model-generated advisory text
- whether new UI-facing code consumes explicit frame contracts instead of recalculating movement
- whether files, functions, or classes are growing past the thresholds in [MAINTAINABILITY.md](MAINTAINABILITY.md)

Prefer small, typed modules and focused tests. Do not create large multipurpose files that mix IO, planning, evaluation, and rendering concerns.
