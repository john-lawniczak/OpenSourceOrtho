# USER_ONE - week 21 import and comparison

Original intraoral scan dated **2026-11-23**, labeled **week 21 by the contributor**.
Imported on 2026-11-24 as progress visit 3. Week labels are reported progress labels,
not elapsed calendar weeks. This is observed source geometry, not simulated motion.

## Measured file checks

The source ZIP passes CRC checks for every one of its 13 members. Both STL byte
lengths exactly match their binary triangle counts. Repository copies have identical
SHA-256 hashes to the archive entries. All six comparison meshes have finite
coordinates, one vertex-connected component and zero duplicate triangles.

| Reported week | Arch | Triangles | Zero-area faces | Edges with >2 faces | Boundary edges |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | maxillary | 330,309 | 0 | 0 | 761 |
| 1 | mandibular | 286,801 | 1 | 1 | 766 |
| 7 | maxillary | 332,227 | 7 | 6 | 2,219 |
| 7 | mandibular | 265,329 | 0 | 0 | 2,513 |
| 21 | maxillary | 337,285 | 1 | 1 | 772 |
| 21 | mandibular | 276,050 | 0 | 0 | 820 |

Boundary edges are expected for open shells. Counts alone neither distinguish
intentional margins from holes nor establish anatomical fidelity. Vertex connectivity
does not establish a manifold surface. No geometry was repaired, smoothed, rescaled,
decimated, recentered or registered in the stored STL files.

## Advisory comparison and rating

These model-generated interpretations passed `lint_finding()` before export.
That checks language, not correctness. The ratings are subjective research-data
scores, not scanner accuracy, clinical quality or treatment-effectiveness scores.

| Rank | Visit | Research-data score |
| --- | --- | ---: |
| Joint first | Week 1 | 8.50 / 10.00 |
| Joint first | Week 21 | 8.50 / 10.00 |
| Third | Week 7 | 7.50 / 10.00 |

Two decimal places follow the requested format; they do not imply that 0.01-point
differences are measurable. Weights and deductions are in `quality-scores.json`.

**Visual coverage.** The overview renders show continuous-looking crown rows and recognizable surface detail in all three visits. Week 7 has more irregular peripheral margins. Week 21 retains ragged soft-tissue scan edges. These are unverified visual impressions; complete anatomy, fine defects and attachment identities were not independently established.

**Topology comparison.** Week 21 resembles week 1 in basic mesh health: one zero-area face and one edge with more than two incident faces across each pair. Week 7 has seven zero-area faces and six such edges, all in its upper scan. All six meshes have one vertex-connected component, zero duplicate triangles and finite coordinates. Open-shell boundary edges include intentional margins; lower counts alone do not prove better accuracy.

**Coordinate and density limits.** Weeks 1 and 21 carry shell_occlusion export labels; week 7 carries shell_teethup labels. This makes the week 21 export more convenient for preserving the recorded upper/lower relationship, but matching source transformations do not validate bite accuracy. Triangle density is broadly similar across visits and does not establish a resolution or scanner-accuracy improvement.

**Unmeasured accuracy.** Week 21 scale remains unverified, and no independent reference surface, repeat scan, self-intersection analysis or cross-visit registration was used. The scores cannot quantify true anatomical fidelity. Week 21 is an original observed scan, not an inferred pose or reviewed treatment plan.

Week 21 has 337,285 upper and 276,050 lower triangles. Median triangle-edge lengths
are approximately 0.169 and 0.169 source units, versus 0.165/0.167 at week 1 and
0.168/0.165 at week 7. These are mesh sampling statistics, not physical resolution.
The slightly greater week 21 triangle count than week 7 does not mean greater accuracy.

## Extracted export information

- Scan date: November 23, 2026, explicitly present in HTML and prescription PDF.
- Export: November 24, 2026, 16:45:51 UTC (11:45:51 AM America/New_York).
- Scanner model: Element 5D, from the prescription PDF.
- Procedure: Study Model / iRecord; PDF status: Completed (workflow status only).
- Export XML schemas: 3.0 and 5.0; scanner software: 2.22.0.51; CaaS: 1.0.0.49.
- Recorded range: Universal/ADA 1-16 upper, 17-32 lower. This is not a verified tooth inventory.
- Two whole-arch jaw STL surfaces with `shell_occlusion` names; no separate bite STL.
- Both XML transform arrays are diag(-1,-1,1,1). They describe already-used export
  transforms, not a cross-visit registration; they have not been reapplied.
- `Modeled=False`; treatment-stage code 0 is unmapped and does not establish week/tray.
- Prescription notes are blank. No tooth-motion measurements, segmentation labels,
  reviewed treatment plan, scale certificate or scanner-accuracy report was supplied.
- Six JPG rendered views, two XML files, one HTML record, one prescription PDF and
  one vendor logo accompany the two STLs. The JPGs are rendered views, not 3D geometry.

## Storage and reproducibility

The contributor authorized publication on November 24, 2026 of the unchanged STL
pair, reviewed source-rendered JPGs, redacted PDF/export metadata and comparisons.
The original identifying paperwork remains excluded. Individual public assets are
listed in the case-root consent.json. Public availability follows the repository's
filtered release process; a private development push alone does not publish them.

Week 21 is connected to interactive scan history with download links and source
views. Its exported upper/lower coordinates are preserved together; this is not
bite validation. Painting saves are source-bound to week 21. Weeks 8-17 and 19-20
remain unfitted, and earlier fitted motion is unchanged.

Reproduce the measured comparison from the repository root:

```bash
MPLCONFIGDIR=/private/tmp/ortho-week21/matplotlib .venv/bin/python \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/evaluate_comparison.py
```

`comparison-views.png` uses independent camera orientations and panel fitting,
not cross-time registration or a bite overlay. `week-21-views.png` shows three views
per original arch. Scoring is an explicitly subjective review and is not regenerated
by the geometry-only script.
