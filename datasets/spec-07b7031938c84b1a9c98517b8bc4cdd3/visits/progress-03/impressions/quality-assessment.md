# USER_ONE — week 21 upper impression

**7.50/10.00 for exploratory scan usability.** Retain this capture; one targeted repeat is worthwhile for checking the posterior opening and cavity walls. This rating is subjective, not measured accuracy, and uses a different rubric from the earlier dental/cast scores.

Impression: November 23, 2026. Digitization: November 24, per contributor. Imported November 25. No coating or manual alteration reported. Original exported bytes preserved.

| Criterion | Points | Maximum |
| --- | ---: | ---: |
| File integrity/basic topology | 1.75 | 2.00 |
| Visible arch/cavity coverage | 3.25 | 4.00 |
| Visible local detail | 1.75 | 2.00 |
| Provenance, calibration and repeat evidence | 0.75 | 2.00 |

[Physical upper impression photograph](upper-impression-photo.png). The contributor confirmed on November 25 that it shows the same condition as the scan. Photo acquisition date is unspecified. Embedded metadata was removed and orientation applied; decoded RGB pixels are preserved losslessly. Original photo remains local.


## Measured file properties

- 216,287 triangles; 108,980 unique vertices; one connected component.
- Finite coordinates; no duplicate triangles; four zero-area triangles and four edges incident to more than two faces.
- 1,689 open edges in three connected boundary groups (1,305, 373 and 11 edges). Most are perimeter boundaries; the small internal opening is highlighted in boundary-detail.png. Open edges alone are not an accuracy score.
- Extents: 74.17 × 68.09 × 32.06 in unverified source units; no calibrated millimeter claim.
- No geometry repair, decimation, normal reversal, registration, scaling or hole filling was applied during this review.

**Same-condition photograph.** The contributor confirms the attached photograph shows this upper impression in the exact condition of the STL capture. Deep shadowed cavities and thin inter-cavity material are visible; dark recesses alone do not establish tears or missing material. Photos provide physical context, but no point-by-point photo-to-mesh mapping or dimensional validation was performed. The 7.50 score remains a provisional scan-usability judgment.

**Coverage.** The six views show a connected upper-arch impression with recognizable anterior and posterior tooth cavities. Most open edges follow the outer/inner scan margins. This is useful exploratory acquisition data; a connected surface alone cannot establish complete cavity capture.

**Local opening.** One small internal boundary has 11 edges near a posterior cavity: right side of the +Z image, left side of the -Z image. Its bounds span about 0.87 by 0.87 by 1.10 unverified source units. No anatomical left/right or tooth number is assigned. Whether the opening comes from occlusion during scanning, material damage, or processing is unresolved.

**Detail limits.** Several grooves and transitions look rounded in the rendered mesh. Impression detail, optical capture and scanner reconstruction cannot be separated from this single export. The visible surface does not establish submillimeter accuracy, capture of every undercut, or agreement with the dental STL.

**Rescan recommendation.** Retain this scan for exploratory comparison. One targeted second capture is worthwhile if studying the acquisition process: view the small posterior opening and deep cavity walls from additional oblique angles, without flexing or altering the impression. Keep it as a separate original export. Repeating the same view is unlikely to resolve occlusion; a physical tear cannot be recovered by rescanning.

**Interpretation.** This is a negative-impression surface, not a direct observation of tooth crowns or a new treatment week. No dental-reference registration, calibrated accuracy measurement, or independent repeatability check was performed. Reversing normals alone does not recover missing geometry. The existing dental upper/lower bite coordinates and motion data are unchanged.

**Provenance.** The contributor reports an original November 23 week 21 impression digitized one day later, without coating or manual alteration in JMStudio. The export header identifies JMStudio v2.4.19.0131. Physical condition, storage effects and internal fusion settings remain unverified; no raw scanner project was supplied.

## Acquisition follow-up

Support the original impression without flexing it. Capture the cavity side from multiple oblique views, targeting the magenta internal opening and steep walls. Preserve this file and the second capture separately; export before any optional repairs, and keep the scanner project if available. Compare coverage and independently registered overlap before merging. If the physical cavity is torn or absent, another optical pass cannot restore it.

Deep undercuts and narrow cavities can be difficult even for dedicated impression workflows; see [3Shape's impression-scanning demonstration](https://www.youtube.com/watch?v=03gmQnwjAZE). This does not establish Fox performance on this specimen.

## Reproduction

From the repository root with the local NumPy/SciPy/Matplotlib environment:

```sh
MPLCONFIGDIR=/private/tmp/ortho-matplotlib PYTHONPATH=. .venv/bin/python datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/impressions/evaluate_scan.py
PYTHONPATH=. .venv/bin/python datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/impressions/build_assessment.py
python3 tools/build_dataset_catalog.py
```
