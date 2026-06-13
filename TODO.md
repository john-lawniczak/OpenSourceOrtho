# TODO

This file tracks only work that still needs implementation. Completed phases,
historical status notes, and already-shipped reference items belong in git
history, release notes, or the relevant docs instead of this active list.

## Product Goal

OpenSource Ortho is working toward functional coverage of a modern
clear-aligner planning workflow while preserving an explicit safety boundary:
scan intake, segmentation, target setup, side-by-side setup comparison, direct 3D
controls, live restaging, root/bone-aware review, manufacturing-oriented QA,
progress/refinement records, and retention handoff.

Generating geometry never means diagnosis, clinical approval, treatment
clearance, or that physical use is safe. Printing, fit, materials,
post-processing, and any physical use remain the user's own responsibility and
risk. Every output must keep its review tier, manufacturing-readiness status,
provenance, and unresolved data gaps clearly labeled.

## Active Roadmap

No phase-sized implementation items are currently open. New work should be added
here only when it still needs implementation; shipped roadmap phases belong in
release notes, git history, and the relevant feature docs.

## Cross-Cutting Backlog

- Add richer provider-native AI streaming adapters and tool-style plan actions
  while preserving explicit egress consent and advisory-only wording.
- Harden export/audit trails around setup comparison, direct-control edits,
  restaging, and print-package generation.
- Continue broadening real-scan, non-PHI smoke coverage for segmentation,
  rendering, setup comparison, shell QA, and longitudinal benchmarks.
- Keep README, architecture docs, safety docs, and glossary terms synchronized
  whenever user-facing capabilities or data-contribution standards change.
