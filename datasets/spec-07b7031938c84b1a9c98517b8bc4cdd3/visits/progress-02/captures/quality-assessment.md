# Week 18 additional lower capture comparison

USER_ONE contributed data; evaluated November 12, 2026. This assessment covers
`2026-11-12_USER_ONE_lower_week-18_fusion-h-4.stl` and `2026-11-12_USER_ONE_lower_week-18_fusion-h-6.stl`, separate captures at the same reported
week 18 visit. Both original files are retained without repair or registration.

## Measured file properties

| Check | Fusion_H_4 | Fusion_H_6 |
| --- | ---: | ---: |
| Triangles | 581,144 | 587,840 |
| Unique vertices (exact coordinates) | 291,697 | 295,366 |
| Zero-area triangles | 15 | 10 |
| Duplicate triangles | 0 | 0 |
| Boundary edges | 2,276 | 2,934 |
| Edges incident to more than two faces | 15 | 9 |
| Vertex-connected components | 1 | 1 |
| Non-finite face records | 0 | 0 |
| Binary STL length valid | Yes | Yes |

Repository filenames use the November 12 contribution/filing date; acquisition
dates remain unverified. Original source filenames are retained in metadata.

Both SHA-256 hashes match the per-capture manifests and the Desktop source
files. Boundary edges show that neither surface is closed. Counts use exact
coordinate deduplication, without tolerance welding. Scale remains unverified.

## Advisory interpretation

The following model-generated observations passed `lint_finding()` before
export. They remain unverified; the gate checks language, not anatomy.

**Mixed mesh-quality results.** Fusion_H_4 has fewer boundary edges (2,276 versus 2,934), but Fusion_H_6 has fewer zero-area triangles (10 versus 15) and fewer edges incident to more than two faces (9 versus 15). Both have one vertex-connected component, no duplicate triangles, and finite coordinates. These results do not establish an overall accuracy winner.

**Peripheral surface appearance.** In the independent rendered views, Fusion_H_4 appears more compact around the outer margins; Fusion_H_6 shows more conspicuous projecting peripheral surfaces. Both include broad sheet-like surfaces beyond the crown-like regions. Camera orientation, independently fitted panel scale, and approximate depth sorting limit this visual comparison. The views do not determine which scan better reproduces the original teeth.

**Retain both captures for region review.** Fusion_H_4 is worth inspecting first for peripheral cleanup because of its more compact visual outline and lower boundary-edge count, but this is a tentative workflow preference, not a ranking of tooth-surface fidelity. Preserve both original captures. Review corresponding crown boundaries and capture provenance before selecting a segmentation input; mark the contributor-reported front-tooth model chip separately from crown boundaries. Exact tooth identity and chip timing remain unknown.

**Reference evidence remains missing.** No verified scale, independently reviewed tooth surfaces, or common anatomical registration is available for this comparison. Boundary counts depend on scan margins and tessellation; zero-area faces and edge incidence describe topology rather than tooth accuracy. Neither capture establishes tooth movement or reference anatomy. Self-intersections, winding, and vertex manifoldness were not assessed.

**Shared chipped-model limitation.** The contributor confirms both additional captures share one physical lower model and reports a small chip on an unidentified lower front tooth. Agreement between H4 and H6 can describe capture consistency but cannot establish the missing undamaged surface. Keep the chip region unreviewed until its location is marked; do not interpret it as actual tooth damage or tooth movement.

## Evidence and reproduction

- [Independent original-surface views](mesh-views.png).
- [Machine-readable topology inventory](mesh-quality.json).
- [Source-bound, linted findings](quality-findings.json).
- [H4 provenance](fusion-h-4/source-metadata.json) and [H6 provenance](fusion-h-6/source-metadata.json).

From the repository root:

```bash
MPLCONFIGDIR=/private/tmp/ortho-week18-matplotlib .venv/bin/python \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/captures/evaluate_captures.py
```

The script regenerates the measured inventory and figure using all triangles.
Advisory interpretation requires a separate review if the sources or outputs
change. Original November 10 pair evaluations retain their two-scan scope.
The contributor authorized publication of these captures and evaluation artifacts on 2026-11-12; see case-root consent.json.
