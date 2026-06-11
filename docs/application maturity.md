# Application Maturity

This document tracks the three application maturity surfaces on a 10-point
scale. Scores are engineering maturity ratings for this research toolkit, not
clinical clearance, treatment approval, or a statement that physical use is safe.

## Summary

| Surface | Current | What the score means |
|---------|---------|----------------------|
| Track 1: upload -> printable aligner artifacts | ~7/10 | Reviewed real geometry can export reproducible model/shell packages with deterministic QA and fail-closed behavior, but robust mesh processing and material/fit modeling are not complete. |
| Track 2: surface-scan staging + honest review aid | ~7/10 | Surface planning, movement caps, collision/IPR review, segmentation review, and benchmarks are useful and bounded, but more labelled real-scan validation and stronger segmentation are needed. |
| Track 3: CBCT root/bone-aware planning from raw volume | ~1-2/10 | Reviewed anatomy can be represented and used once supplied, but raw CBCT root/bone segmentation and default auto-registration are still future work. |

## Track 1: Upload -> Printable Aligner Artifacts

Current rating: ~7/10.

What exists:

- Scale-gated print export with reproducible model STLs, manifests, hashes, zip,
  and optional email draft.
- Real per-tooth vertices are used only for reviewed segmentation links.
- Proxy/model-only fallback is labeled and fail-closed.
- Aligner-shell export for reviewed real geometry with configurable sheet
  thickness and trusted-axis trim when available.
- Shell QA reports watertightness, connected components, rim closure, approximate
  self-intersection signals, inner/outer clearance, thickness distribution,
  degenerate/sliver input counts, hashes, and manufacturing-readiness verdicts.
- API and print-package payloads surface manufacturing readiness and printer
  tolerance metadata.

Why it is not higher:

- Shell construction is still a vertex-normal approximation.
- There is no robust optional boolean/signed-distance/Minkowski shell backend.
- Self-intersection detection is an approximate deterministic signal, not a full
  triangle-triangle intersection engine.
- There is no full-arch messy fixture corpus or independent known-good shell
  comparison set.
- Material deformation, thermoforming fit, printer calibration, support strategy,
  and physical validation remain outside the software.

What 10/10 would require:

- Robust mesh repair and offset backend behind optional extras, with pure-Python
  fallback preserved.
- Full triangle-level self-intersection and nonmanifold detection.
- Known-good full-arch shell fixtures from an independent mesh pipeline.
- Messy non-PHI fixtures covering holes, islands, thin slivers, inverted winding,
  nonmanifold edges, and trimline edge cases.
- Printer/material tolerance profiles and benchmarked output deltas.
- Clear package-level explanations for every generated, skipped, or downgraded
  artifact.

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
