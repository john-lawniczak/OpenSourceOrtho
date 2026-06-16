# Application Maturity

This document tracks the application maturity surfaces on a 10-point scale.
Scores are engineering maturity ratings for this research toolkit, not clinical
clearance, treatment approval, or a statement that physical use is safe.

**All four surfaces below are active focus areas with a committed target of
≥9/10.** `TODO.md` is the active backlog and currently has no phase-sized
implementation item open; the remaining gap is mainly validation depth,
production-strength optional backends, audit trails, and real-world operating
evidence. A 10/10 is intentionally NOT a target for the geometry tracks: it would
require material deformation, thermoforming fit, printer calibration, and
physical validation, which this safety-boundary-first toolkit deliberately does
not model.

## Summary

| Surface | Current | Target | What the score means |
|---------|---------|--------|----------------------|
| Track 1: upload -> printable aligner artifacts | ~9.0/10 | ≥9/10 | Strong within the software-only scope: reviewed real geometry exports reproducible model/shell packages with real shell QA, robust-backend validation hooks, messy fixtures, and independent full-arch fixtures; physical fit/material/printer validation remains out of scope. |
| Track 2: surface-scan staging + honest review aid | ~8.85/10 | ≥9/10 | Surface planning, movement caps, reviewed full-geometry collision/IPR, segmentation review, guided review UX, real-scan smoke coverage, learned-vs-heuristic benchmark hooks, and hard segmentation quality gates are in place; the remaining weakness is broader labelled real-case validation and production learned weights. |
| Track 3: CBCT root/bone-aware planning from raw volume | ~8.4/10 | ≥9/10 | Phase 12 is implemented as a safety-gated proposal workflow: raw-volume sparse-mask proposals, auto-registration proposals, fail-closed tests, and benchmark metrics exist, but maturity is held back by caller-supplied masks, no bundled clinical-grade volume segmenter, and limited open-volume validation. |
| Track 4: in-app AI assistant (chat) | ~8.5/10 | ≥9/10 | Plan-scoped, auditable, fail-closed connectors now have bounded memory, incremental rendering, provider/model selection, PHI-share gating, and SSE streaming with fallback; provider-native stream adapters and action tooling remain. |

## Track 1: Upload -> Printable Aligner Artifacts

Current rating: ~9.0/10. Target: ≥9/10. The software-only target is reached for
the implemented scope, with the important caveat that physical fit, validated
materials, printer calibration, and clinical authorization are deliberately out
of scope.

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

What preserving or improving the ≥9/10 target requires:

- Keep the robust backend and benchmark corpus green as new shell features land.
- Expand reviewed non-PHI real-scan validation where contributors can supply
  consented fixtures.
- Printer/material tolerance profiles and benchmarked output deltas remain
  outside the current software target unless the product scope changes.

## Track 2: Surface-Scan Staging + Honest Review Aid

Current rating: ~8.8/10. Target: ≥9/10.

What exists:

- Surface-only planning with explicit data gaps and review tiers.
- Movement caps, clinical controls, fixed teeth, exclusions, IPR metadata, and
  timeline projection.
- Setup comparison now includes captured/saved/generated provenance labels,
  live-restaged candidates, side-by-side workspace summaries, and explicit
  non-overwriting promotion into the editor.
- Direct technician controls cover translation, intrusion/extrusion, rotation,
  crown tip, crown torque, crown angulation, and same-arch response proposals
  while failing closed without confirmed units and reviewed segmentation.
- Auto-segmentation proposal path with human review and per-tooth mesh exports.
- Hard segmentation quality gates now distinguish a reviewable draft from a
  production-candidate segmentation using tooth-count, compactness, and
  confidence checks. The `/api/segment` response exposes per-arch gate reports,
  and the validation benchmark tracks bundled real-scan reviewable vs.
  production-candidate counts.
- A manifest-driven labelled real-scan benchmark path exists for external
  non-PHI or consented cases. Cases must declare PHI removal, consent, and
  commercial-use permission before they are scored, and
  `orthoplan segmentation-benchmark --manifest ...` reports local accuracy,
  region purity, tooth counts, and review-burden delta versus the fallback. This
  keeps questionable datasets or weights from silently becoming production
  evidence.
- One-click plan generation chooses the best available target in this order:
  authored movement, reviewed landmarks/space analysis, segmented per-tooth crown
  geometry, or a clearly labelled educational template when only a raw scan is
  loaded. The raw-scan fallback is not a tooth-specific path proposal.
- Adjacent same-arch collision/IPR review using reviewed full-triangle geometry
  from the mesh workspace when available, with capped samples and bbox fallback.
- Synthetic benchmarks for segmentation, movement, collision/IPR, shell
  thickness, messy shells, and sampled-vs-triangle collision distance deltas.
- Real-scan segmentation smoke coverage on the bundled canonical Orthocad sample
  scans, including crown-count regression floors.
- Learned-vs-heuristic benchmark hooks on synthetic clean, crowded, and
  contacting-crown arches; the heuristic/hybrid path remains the no-dependency
  fallback.
- A guided review dashboard leads the "Review your plan" step with a single
  honest verdict (`ready` / `needs-review` / `cannot-assess`) plus edit-diff,
  warnings, root/bone, and print-readiness cards. It classifies findings by
  severity so only `warning`-severity findings are treated as blocking review
  concerns; `info`/`notice` context (e.g. the `root-bone-context` info finding
  emitted for healthy root/bone-aware plans, and `*-scale-unconfirmed`
  skipped-check notices) never flips the verdict or fabricates 3D overlay chips.

Why it is not higher:

- Segmentation still needs more labelled real-scan validation across varied
  scanners, arch shapes, crowding patterns, and restorations.
- Learned ONNX segmentation is wired and benchmarked, but production-quality
  weights and real-case benchmark deltas are still optional/offline expansion.
- The current no-dependency segmenter is useful for review proposals and bundled
  real-scan crown-count smoke tests, but it is not a production-quality automatic
  tooth-path system: clean per-tooth crown boundaries and target setup still
  depend on review, landmarks, or stronger optional segmentation.
- No license-clear production weights or labelled real-scan corpus are bundled.
  The new gates therefore block the current heuristic from being treated as a
  production candidate on real scans.
- Occlusion dynamics, bite force, periodontal status, and biological response are
  intentionally not inferred from STL surfaces.

What reaching the ≥9/10 target requires:

- Reviewed open-dataset benchmarks with clear provenance and no PHI.
- Stronger segmentation backend or supplied weights with measurable improvement
  on labelled crowded/contacting real arches.
- A labelled, license-clear real-scan corpus large enough to make the production
  gate meaningful across scanner brands, arch shapes, restorations, crowding, and
  missing-tooth cases.
- Full-geometry collision/IPR already exists for reviewed workspace assets; the
  next lift is stronger segmentation so more cases need less manual cleanup.
- Regression dashboards that track metric deltas across benchmark releases.

## Track 3: CBCT Root/Bone-Aware Planning From Raw Volume

Current rating: ~8.4/10. Target: ≥9/10. Phase 12 is implemented for the intended
safety-gated scope: raw-volume and automatic-registration outputs are proposals
only until reviewed and explicitly accepted. The lower score reflects true layer
maturity beyond that shipped checklist: sparse masks are caller-supplied, and
open-volume validation is still thin.

What exists:

- CBCT/DICOM metadata intake with PHI stripping and no volume bytes in plan JSON.
- Registration model with accepted quality gate.
- Reviewed anatomy records for roots, tooth axes, and alveolar bone.
- Root/bone-aware checks and root-aware movement when trusted reviewed anatomy is
  present.
- Fail-closed behavior when registration or reviewed anatomy is unavailable.
- Optional raw-volume sparse-mask proposal path that emits `PROPOSED` root
  centerlines, tooth axes, and alveolar-bone records into the reviewed-anatomy
  pipeline without storing volume bytes in plan JSON.
- Automatic STL-to-CBCT registration proposal wrapper with quality metrics and
  explicit human acceptance gating.
- Synthetic volume benchmarks and fail-closed tests proving unaccepted
  registration, proposed anatomy, optional-extra absence, and rejected anatomy do
  not promote a plan to trusted root/bone-aware behavior.
- Proposal quality aids including connected-component cleanup, dropped-noise
  counts, field-boundary truncation flags, centerline metrics, and confidence
  notes for reviewer attention.

Why it is not higher:

- The raw-volume path consumes caller-supplied sparse masks/labels; it is not a
  bundled clinical-grade CBCT segmentation model with validated weights.
- Auto-registration remains a proposal workflow and never becomes trusted without
  explicit human acceptance.
- Benchmarks are synthetic/open and fail-closed oriented; broader reviewed
  open-volume cases and real-world validation remain future work.
- Volume viewing, clinical fit guarantees, diagnosis, material response, and
  physical-use validation remain outside the core software target.

What reaching the ≥9/10 target requires:

- No remaining Phase 12 implementation item is tracked in `TODO.md`; the
  safety-gated proposal workflow is complete for the current scope.
- Keep raw-volume proposal, auto-registration, and fail-closed benchmark tests
  green as the model contracts evolve.
- Expand reviewed non-PHI/open-volume benchmark cases with clear provenance.
- Add stronger optional segmentation backends or external-tool adapters when
  model weights and datasets can be used under compatible licenses.
- Preserve the untrusted-proposal boundary: raw-volume outputs and automatic
  registrations must require deterministic checks plus explicit human review
  before any root/bone-aware behavior is trusted.

## Track 4: In-App AI Assistant (Chat)

Current rating: ~8.5/10. Target: ≥9/10.

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

## End-To-End Reality Check

The current flow is strongest from reviewed geometry to reproducible print
artifacts. It can ingest surface scans, propose/review segmentation, generate a
cap-respecting staged plan from authored movement, landmarks, or reviewed crown
geometry, run deterministic checks, and export models/shells with manifest and
shell QA.

The weakest link in the full "teeth scan -> automatically suggest tooth path ->
print aligners" ambition is still the middle: automatic path suggestion from a
raw scan is not yet a production-grade, case-specific setup engine. The code has
a clear generation hierarchy, a learned-segmentation seam, hard segmentation
quality gates, and a manifest path for labelled real-scan validation, but
production learned weights, a sizeable labelled real-case corpus, and
longitudinal outcome data are not bundled. Until those exist, automatically
generated plans remain reviewable proposals, and raw-scan-only generation is
explicitly educational.
