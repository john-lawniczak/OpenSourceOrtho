# Application Maturity

This document tracks the application maturity surfaces on a 10-point scale.
Scores are engineering maturity ratings for this research toolkit, not clinical
clearance, treatment approval, or a statement that physical use is safe.

**All four surfaces below are active focus areas with a committed target of
≥9/10.** The ordered work to reach each target lives in `TODO.md` (the
"Order of operations to ≥9/10" section). A 10/10 is intentionally NOT a target for the geometry
tracks: it would require material deformation, thermoforming fit, printer
calibration, and physical validation, which this safety-boundary-first toolkit
deliberately does not model.

## Summary

| Surface | Current | Target | What the score means |
|---------|---------|--------|----------------------|
| Track 1: upload -> printable aligner artifacts | ~9/10 | ≥9/10 | Reviewed real geometry exports reproducible, spec-correct model/shell packages with real shell QA, a robust Open3D distance-offset backend, messy-corpus validation, and independent full-arch fixtures; material/fit modeling remains out of scope. |
| Track 2: surface-scan staging + honest review aid | ~7.8/10 | ≥9/10 | Surface planning, movement caps, reviewed full-geometry collision/IPR, segmentation review, a severity-aware guided review dashboard, and benchmark deltas are useful and bounded, but learned segmentation and broader real-case benchmarks still need work. |
| Track 3: CBCT root/bone-aware planning from raw volume | ~1-2/10 | ≥9/10 | Reviewed anatomy can be represented and used once supplied, but raw CBCT root/bone segmentation and default auto-registration are still future work. This is the longest road by far. |
| Track 4: in-app AI assistant (chat) | ~8.5/10 | ≥9/10 | Plan-scoped, auditable, fail-closed connectors now have bounded memory, incremental rendering, provider/model selection, PHI-share gating, and SSE streaming with fallback; provider-native stream adapters and action tooling remain. |

## Track 1: Upload -> Printable Aligner Artifacts

Current rating: ~9/10. Target: ≥9/10 (ordered path: `TODO.md` "Order of
operations", Phase 9.1 through Phase 9.4).

What exists:

- Scale-gated print export with reproducible model STLs, manifests, hashes, zip,
  and optional email draft.
- Real per-tooth vertices are used only for reviewed segmentation links.
- Proxy/model-only fallback is labeled and fail-closed.
- Aligner-shell export for reviewed real geometry with configurable sheet
  thickness and trusted-axis trim when available.
- Printer XY/Z dimensional compensation is baked into the exported shell
  geometry (not just reported in the manifest) and the applied values are echoed
  back through the shell QA block.
- Exported STL files carry real per-facet unit normals computed from triangle
  winding, not placeholder zero normals.
- Shell QA reports watertightness, connected components, rim closure, a real
  triangle-triangle self-intersection count (Möller narrow phase behind an AABB
  broad phase), nonmanifold-edge detection, inner/outer clearance, thickness
  distribution, degenerate/sliver input counts, hashes, and
  manufacturing-readiness verdicts.
- Every shell artifact carries a named ``failed_checks`` list explaining exactly
  which deterministic check downgraded it to ISSUES (or that it passed).
- An independent analytic oracle (closed-form slab volume) plus synthetic messy
  fixtures (self-intersection, nonmanifold edges, disconnected islands, inverted
  winding, degenerate input) verify the QA against ground truth that does not
  come from the builder itself.
- API and print-package payloads surface manufacturing readiness and printer
  tolerance metadata, and the UI shows the readiness verdict, applied
  compensation, and per-stage shell QA (named failed checks and skip reasons) in
  both the guided print step and the technician print panel.
- A `shell_backend` setting selects between the always-on pure-Python shell and an
  optional `robust` path behind the `mesh-processing` extra; when the extra is
  absent the export falls back to pure-Python and records the downgrade in the
  manifest, API, and UI rather than silently changing geometry. The robust path
  uses Open3D repair plus distance-field offset correction.
- A dedicated CI lane installs `mesh-processing` and runs robust backend tests.
- The validation benchmark records robust-vs-pure shell metrics on messy non-PHI
  fixtures and an independent full-arch generator, including thickness deltas,
  hash deltas, self-intersections, and nonmanifold edges.
  See [aligner-shell-backend.md](aligner-shell-backend.md).

Why it is not higher:

- The pure-Python no-extra shell remains a vertex-normal approximation; the
  Open3D robust backend is optional and its validation is only exercised in the
  mesh-processing CI lane.
- The bundled known-good and messy fixtures are non-PHI synthetic/open fixtures;
  broader messy real-scan corpus validation is still future work.
- Material deformation, thermoforming fit, printer calibration, support strategy,
  and physical validation remain outside the software.

What reaching the ≥9/10 target requires:

- Keep the robust backend and benchmark corpus green as new shell features land.
- Expand reviewed non-PHI real-scan validation where contributors can supply
  consented fixtures.
- Printer/material tolerance profiles and benchmarked output deltas remain
  outside the current software target unless the product scope changes.

## Track 2: Surface-Scan Staging + Honest Review Aid

Current rating: ~7.8/10. Target: ≥9/10 (ordered path: `TODO.md` "Order of
operations", Phase 14).

What exists:

- Surface-only planning with explicit data gaps and review tiers.
- Movement caps, clinical controls, fixed teeth, exclusions, IPR metadata, and
  timeline projection.
- Auto-segmentation proposal path with human review and per-tooth mesh exports.
- Adjacent same-arch collision/IPR review using reviewed full-triangle geometry
  from the mesh workspace when available, with capped samples and bbox fallback.
- Synthetic benchmarks for segmentation, movement, collision/IPR, shell
  thickness, messy shells, and sampled-vs-triangle collision distance deltas.
- A guided review dashboard leads the "Review your plan" step with a single
  honest verdict (`ready` / `needs-review` / `cannot-assess`) plus edit-diff,
  warnings, root/bone, and print-readiness cards. It classifies findings by
  severity so only `warning`-severity findings are treated as blocking review
  concerns; `info`/`notice` context (e.g. the `root-bone-context` info finding
  emitted for healthy root/bone-aware plans, and `*-scale-unconfirmed`
  skipped-check notices) never flips the verdict or fabricates 3D overlay chips.

Why it is not higher:

- Segmentation still needs more labelled real-scan validation.
- Learned ONNX segmentation is still optional and not yet benchmarked as a clear
  improvement over the heuristic on crowded/contacting arches.
- Occlusion dynamics, bite force, periodontal status, and biological response are
  intentionally not inferred from STL surfaces.

What reaching the ≥9/10 target requires:

- Reviewed open-dataset benchmarks with clear provenance and no PHI.
- Stronger segmentation backend with measurable improvement on crowded/contacting
  arches.
- Full-geometry collision/IPR already exists for reviewed workspace assets; the
  next lift is stronger segmentation so more cases need less manual cleanup.
- Regression dashboards that track metric deltas across benchmark releases.

## Track 3: CBCT Root/Bone-Aware Planning From Raw Volume

Current rating: ~1-2/10. Target: ≥9/10 (ordered path: `TODO.md` "Order of
operations", Wave 4 / Phase 12a -> 12b -> 12c). The longest road by far -
raw-volume segmentation plus auto-registration plus validation.

What exists:

- CBCT/DICOM metadata intake with PHI stripping and no volume bytes in plan JSON.
- Registration model with accepted quality gate.
- Reviewed anatomy records for roots, tooth axes, and alveolar bone.
- Root/bone-aware checks and root-aware movement when trusted reviewed anatomy is
  present.
- Fail-closed behavior when registration or reviewed anatomy is unavailable.

Why it is not higher:

- The application does not yet segment roots or bone from raw CBCT volumes.
- Auto-registration is not a default accepted workflow.
- There are no volume-processing fixtures or reviewed open CBCT benchmark cases.

What reaching the ≥9/10 target requires:

- Optional volume-processing backend that proposes roots, axes, and bone
  boundaries from CBCT while keeping proposals untrusted until human review.
- Auto-registration proposal path with quality metrics and human acceptance.
- Synthetic and reviewed open-volume benchmarks.
- End-to-end fail-closed tests proving raw-volume absence, optional-extra
  absence, and rejected anatomy never promote a plan to trusted root/bone-aware
  behavior.

## Track 4: In-App AI Assistant (Chat)

Current rating: ~8.5/10. Target: ≥9/10 (ordered path: `TODO.md` "Order of
operations", future provider/action tooling).

What exists:

- Plan-scoped, auditable chat gateway that packages a bounded plan context,
  bounded conversation memory, and records which scope was shared.
- Connector catalog (local helper, OpenAI, Claude Code, MCP, open-source) with
  per-request credentials that are never stored.
- Cursor-style provider -> model selection, connector model catalogs,
  per-provider remembered model choices, and custom self-hosted model IDs.
- Incremental message rendering, Enter-to-send, and token streaming where the
  connector supports it, with a non-streaming JSON fallback.
- Safety posture: model output is kept separate from deterministic findings, and
  any model-generated finding still passes `lint_finding()` before display/export.
- PHI-share acknowledgement and `shares_patient_data` labeling before any
  non-local provider receives plan context; the local helper is the default and
  needs no key.

Why it is not higher:

- Streaming is implemented through the common SSE path, but richer
  provider-native stream adapters could expose finer-grained status and errors.
- The assistant does not yet propose tool-style plan actions for deterministic
  review, acceptance, or rejection workflows.
- It remains advisory: deterministic validation still owns findings and clinical
  boundary language.

What reaching the ≥9/10 target requires:

- Provider-native streaming adapters for the most important connectors.
- Tool-style proposed actions that remain untrusted until deterministic review
  and explicit user acceptance.
- Better transcript/export audit views for provider, model, PHI-share scope, and
  request timing.
- All safety constraints above preserved unchanged.
