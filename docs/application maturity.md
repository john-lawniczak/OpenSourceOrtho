# Application Maturity

This document tracks the three application maturity surfaces on a 10-point
scale. Scores are engineering maturity ratings for this research toolkit, not
clinical clearance, treatment approval, or a statement that physical use is safe.

## Summary

| Surface | Current | What the score means |
|---------|---------|----------------------|
| Track 1: upload -> printable aligner artifacts | ~8/10 | Reviewed real geometry exports reproducible, spec-correct model/shell packages with a real triangle-triangle self-intersection + nonmanifold engine, per-artifact pass/fail explanations, and an analytic known-good oracle; a robust boolean/offset mesh backend and material/fit modeling are still out of scope. |
| Track 2: surface-scan staging + honest review aid | ~7/10 | Surface planning, movement caps, collision/IPR review, segmentation review, and benchmarks are useful and bounded, but more labelled real-scan validation and stronger segmentation are needed. |
| Track 3: CBCT root/bone-aware planning from raw volume | ~1-2/10 | Reviewed anatomy can be represented and used once supplied, but raw CBCT root/bone segmentation and default auto-registration are still future work. |

## Track 1: Upload -> Printable Aligner Artifacts

Current rating: ~8/10.

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
  optional `robust` path (Open3D mesh repair) behind the `mesh-processing` extra;
  when the extra is absent the export falls back to pure-Python and records the
  downgrade in the manifest, API, and UI rather than silently changing geometry.
  See [aligner-shell-backend.md](aligner-shell-backend.md).

Why it is not higher:

- Shell construction is still a vertex-normal approximation. The optional robust
  backend currently does mesh repair only; a true boolean/signed-distance
  (Minkowski) offset is not implemented, and the robust path is not yet validated
  in CI (Open3D is not installed there).
- The known-good comparison is analytic/primitive-level and the messy corpus is
  synthetic; there is no full-arch known-good set from an independent mesh
  pipeline and no messy real-scan corpus.
- Material deformation, thermoforming fit, printer calibration, support strategy,
  and physical validation remain outside the software.

What 10/10 would require:

- Robust mesh repair and offset backend behind optional extras, with pure-Python
  fallback preserved.
- Known-good full-arch shell fixtures from an independent mesh pipeline.
- Messy non-PHI full-arch fixtures covering holes, islands, thin slivers,
  inverted winding, nonmanifold edges, and trimline edge cases beyond the current
  synthetic unit fixtures.
- Printer/material tolerance profiles and benchmarked output deltas.

## Track 2: Surface-Scan Staging + Honest Review Aid

Current rating: ~7/10.

What exists:

- Surface-only planning with explicit data gaps and review tiers.
- Movement caps, clinical controls, fixed teeth, exclusions, IPR metadata, and
  timeline projection.
- Auto-segmentation proposal path with human review and per-tooth mesh exports.
- Adjacent same-arch collision/IPR review using bbox prefiltering plus capped
  representative surface samples.
- Synthetic benchmarks for segmentation, movement, collision/IPR, and shell
  thickness.

Why it is not higher:

- Segmentation still needs more labelled real-scan validation.
- Contact/IPR uses capped sample points rather than full triangle-level distance.
- Occlusion dynamics, bite force, periodontal status, and biological response are
  intentionally not inferred from STL surfaces.

What 10/10 would require:

- Reviewed open-dataset benchmarks with clear provenance and no PHI.
- Stronger segmentation backend with measurable improvement on crowded/contacting
  arches.
- More complete mesh proximity/contact analysis using robust geometry when
  optional dependencies are installed.
- Regression dashboards that track metric deltas across benchmark releases.

## Track 3: CBCT Root/Bone-Aware Planning From Raw Volume

Current rating: ~1-2/10.

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

What 10/10 would require:

- Optional volume-processing backend that proposes roots, axes, and bone
  boundaries from CBCT while keeping proposals untrusted until human review.
- Auto-registration proposal path with quality metrics and human acceptance.
- Synthetic and reviewed open-volume benchmarks.
- End-to-end fail-closed tests proving raw-volume absence, optional-extra
  absence, and rejected anatomy never promote a plan to trusted root/bone-aware
  behavior.
