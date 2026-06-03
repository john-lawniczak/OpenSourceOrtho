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
