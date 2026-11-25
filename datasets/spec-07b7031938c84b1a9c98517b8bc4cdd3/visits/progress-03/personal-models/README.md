# USER_ONE — week 21 personal models

Six original STL exports from four contributor-made physical casts, linked to the
November 23, 2026 week 21 dental intraoral visit (`progress-03`). The contributor
reports acquisition on the same day as the dental scan. Import date: November 24.

| Physical cast | Original exports | Repository files |
| --- | --- | --- |
| Upper Model 1 | Fusion_C_1, Fusion_C_2, Fusion_C_3 | [upper-1-c1.stl](upper-1-c1.stl), [upper-1-c2.stl](upper-1-c2.stl), [upper-1-c3.stl](upper-1-c3.stl) |
| Upper Model 2, more chipped | Fusion_C_4 | [upper-2-c4.stl](upper-2-c4.stl) |
| Lower Model 1 | Fusion_C_5 | [lower-1-c5.stl](lower-1-c5.stl) |
| Lower Model 2 | Fusion_C_6 | [lower-2-c6.stl](lower-2-c6.stl) |

The contributor confirmed that C1/C2/C3 are separate scans of the same physical
upper cast. The inventory preserves that account; measured C1/C2 geometry is highly
correlated, so it must not inflate the effective independent sample count.

- [Assessment and scores](quality-assessment.md)
- [Original mesh views](cast-overview.png)
- [Dental comparison views](dental-comparison.png)
- [Source hashes and acquisition provenance](source-metadata.json)
- [Topology inventory](mesh-inventory.json)
- [Comparison distances and rigid transforms](dental-comparison.json)
- [Structured scores and linted advisory findings](summary.json)

The week 21 scan-history panel exposes these specifically indexed companion
records through `/api/sample-personal-models`. Original dental observations remain
unchanged. Cast scans do not establish an upper/lower bite relationship or tooth
motion. `record-assets.json` binds each download to its SHA-256.

The contributor authorized these individually listed assets for public reuse on
November 24, 2026. Each download requires case consent and a matching SHA-256.
Preserve the original STLs; rendered views and rigid transforms are separate
analysis artifacts. Reported chips concern the physical casts, not actual teeth.

**C6 clarification:** Lower Model 2 broke into two pieces and was held together
with clay during scanning. Original relative fragment positions are unverified.
Its distances and 5.25/10.00 research-usability score describe this reassembled
specimen, not intact-arch accuracy or scanner performance. Rescanning that assembly
cannot recover missing material or establish the original arch shape.

Same-day original dental references: [upper STL](../progress-03-upper.stl) and
[lower STL](../progress-03-lower.stl). These eight week 21 files represent one
intraoral pair and six cast captures, not eight independent visits.

The scan-history panel includes typed acquisition provenance and repeat-object grouping.
See the [capture review workflow](../../../../../docs/CAPTURE_PROVENANCE.md) for
validation commands and impression/retired-aligner research capture guidance.
