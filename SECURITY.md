# Security Policy

## Scope and safety boundary

OpenSource Ortho is a **research/education toolkit, not a medical device**. It
does not diagnose, decide treatment safety or suitability, or replace a licensed
dental professional. Please read [docs/SAFETY.md](docs/SAFETY.md). Reports that a
finding "should have approved/cleared a plan" are out of scope by design - the
software intentionally never makes those claims.

In-scope security issues include, for example:

- ways to make model-generated output bypass the `lint_finding()` safety gate
- path traversal, SSRF, or unsafe file handling in `orthoplan/server.py` or the
  mesh/print/export paths
- leakage of an AI-connector API key (it must stay session-only and never be
  persisted, logged, or echoed back)
- any path that stores or transmits patient-derived data contrary to the stated
  boundary

## Reporting a vulnerability

Please **do not open a public issue for a security vulnerability.**

- Preferred: open a [private security advisory](https://github.com/john-lawniczak/OpenSourceOrtho/security/advisories/new).
- Or email **lawniczak.john@gmail.com** with steps to reproduce and impact.

You can expect an acknowledgement within a few days. This is a volunteer-run
open-source project, so timelines are best-effort. Please give us a reasonable
window to fix an issue before public disclosure.

## Supported versions

Only the latest release on `main` is supported. There are no backported fixes.
