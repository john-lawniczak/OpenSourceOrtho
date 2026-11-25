# USER_ONE — week 21 personal cast assessment

Four physical casts, six original STL exports, reported same-day acquisition on 2026-11-23. Contributor-authorized public companion records for progress-03.

| Physical cast | Score / 10.00 | Preferred inspection file |
| --- | ---: | --- |
| Upper Model 1 | 7.25 | upper-1-c3.stl |
| Upper Model 2 | 6.00 | upper-2-c4.stl |
| Lower Model 1 | 7.50 | lower-1-c5.stl |
| Lower Model 2 | 5.25 | lower-2-c6.stl |

Equal-weight mean across four casts: **6.50/10.00**. Upper Model 1 is counted once despite its three scans.

Rubric: file integrity/basic topology 2 points; visible coverage/cast preservation 4; exploratory reference agreement 3; provenance/calibration 1. The component scores appear in summary.json. Chips and missing local surfaces matter more than triangle count. Scores are subjective, not clinical evaluations or hundredth-point measurements.

## Same-day reference comparison

| Scan | Dental→cast median | Dental→cast p95 | Dental samples within 0.5 source units |
| --- | ---: | ---: | ---: |
| upper-1-c1 | 0.161 | 2.865 | 81.0% |
| upper-1-c2 | 0.161 | 2.863 | 80.9% |
| upper-1-c3 | 0.160 | 1.376 | 86.7% |
| upper-2-c4 | 0.146 | 2.927 | 76.7% |
| lower-1-c5 | 0.102 | 1.355 | 88.6% |
| lower-2-c6 | 0.526 | 2.009 | 47.9% |

All distances use **unverified source units**, not calibrated millimeters. Registration is rigid only: no scaling, deformation, repairs or hole filling. All 16,000 held-out dental samples are included in the reported distances, including samples excluded from the 80%-trimmed fitting step. Crown-only segmentation was not performed. Boundary/soft-tissue differences can dominate the tails; a low median cannot rule out important local damage.

## Reviewed advisory interpretations

**Upper Model 1.** Upper Model 1: 7.25/10.00 for cast-scan research usability. Best upper cast in this set. C1/C2 retain recognizable crown surfaces; C3 adds coverage. Boundary losses and unverified scale remain. Three files represent one physical cast, not three independent cast specimens.

**Upper Model 2.** Upper Model 2: 6.00/10.00 for cast-scan research usability. Much of the retained surface aligns closely, but anterior local losses are visible and the contributor labels this cast more chipped. Its low median distance does not capture the importance of missing local detail.

**Lower Model 1.** Lower Model 1: 7.50/10.00 for cast-scan research usability. Strongest overall reference agreement of this set, with most sampled dental surface nearby after rigid fitting. Local mismatch patches remain; casting walls account for some reverse-direction differences.

**Lower Model 2.** Lower Model 2: 5.25/10.00 for cast-scan research usability. Contributor confirms the cast broke into two pieces and was held together with clay during scanning. The score is retained only as a research-usability rating of this assembled specimen. Its fragment positions are unverified; the larger mismatch cannot establish intact-arch accuracy or scanner performance. Reassembly, damage, casting and scan/fitting effects are confounded.

**Score interpretation.** The four physical casts average 6.50/10.00 with equal weight per cast. Scores are quarter-point editorial judgments displayed to two decimals, not measured anatomical accuracy or a rating of contributor skill. No new dental-scan score is assigned; the earlier 8.50 visit score used a different rubric.

**Repeat-capture evidence.** The contributor confirms C1, C2 and C3 are separate scans of Upper Model 1. Nevertheless, C1 and C2 share 97.79% of exact vertex positions and identical face counts/bounds. Retain that provenance, but treat their exported surfaces as highly correlated. They do not supply independent repeatability evidence. C1 versus C3 has a fitted median surface difference of about 0.037 source units, with local outliers; this is same-cast consistency, not accuracy.

**Comparison limits.** Reference-to-cast medians are about 0.16 for Upper Model 1, 0.15 for Upper Model 2, 0.10 for Lower Model 1 and 0.53 for Lower Model 2, in unverified source units. Whole-surface distances include soft-tissue boundaries and local missing surfaces. The dental scan is a useful comparison reference, not independently measured ground truth; rigid fitting can absorb pose differences but not prove anatomical fidelity.

**C6 fracture clarification.** Lower C6 is a two-piece cast supported with clay, per contributor clarification. Its original bytes and computed distances are preserved, but those distances describe an assembled specimen. A new scan of the same assembly cannot recover the original relative fragment positions or missing surfaces. Do not use C6 as an intact lower-arch reference.

**Research value.** Same-day dental and cast scans reduce timing differences when studying the home acquisition workflow. Two physical casts per arch expose between-cast variability, while repeat captures of one cast help assess scanning/export consistency. Damaged models provide examples for detecting incomplete surfaces and reporting uncertainty. This is one contributor and four casts; it does not establish general performance or isolate each source of error.

## Capture provenance review

Typed acquisition records distinguish the physical object, scan session, observed surface, damage, coating and processing history. Unknowns stay explicit. Different hashes do not establish independent repeatability.

**upper-1-c1.stl: Cast-derived proxy.** Intact-arch reference: not_established.
- Distances combine impression, casting, scanning and fitting effects.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Physical condition has not been recorded; mesh connectivity does not establish an intact specimen.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

**upper-1-c2.stl: Cast-derived proxy.** Intact-arch reference: not_established.
- Distances combine impression, casting, scanning and fitting effects.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Physical condition has not been recorded; mesh connectivity does not establish an intact specimen.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

**upper-1-c3.stl: Cast-derived proxy.** Intact-arch reference: not_established.
- Distances combine impression, casting, scanning and fitting effects.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Physical condition has not been recorded; mesh connectivity does not establish an intact specimen.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

**upper-2-c4.stl: Damaged specimen / Cast-derived proxy.** Intact-arch reference: excluded.
- Distances combine impression, casting, scanning and fitting effects.
- Missing surfaces or unverified fragment positions prevent interpreting this specimen as an intact-arch reference. Rescanning cannot restore missing anatomy.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

**lower-1-c5.stl: Cast-derived proxy.** Intact-arch reference: not_established.
- Distances combine impression, casting, scanning and fitting effects.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Physical condition has not been recorded; mesh connectivity does not establish an intact specimen.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

**lower-2-c6.stl: Damaged specimen / Cast-derived proxy.** Intact-arch reference: excluded.
- Distances combine impression, casting, scanning and fitting effects.
- Missing surfaces or unverified fragment positions prevent interpreting this specimen as an intact-arch reference. Rescanning cannot restore missing anatomy.
- Coating status is unknown or a coating was applied. Layer thickness and material compatibility are not measured by this report. Do not coat an appliance that will return to the mouth.
- Processing is recorded or unknown. Preserve source exports; smoothing, filling and scaling can change measured surfaces.
- Distances remain source-coordinate units until scale is independently established; this review does not change units.

## Record and reproduction

- Original scan bytes are preserved and SHA-256 verified in manifest.json.
- mesh-inventory.json records finite coordinates, connected components and topology. Each file is connected, has no duplicate triangles, and has 2–6 zero-area triangles/non-manifold edge incidences. Open edges include intentional scan margins.
- cast-overview.png shows all source triangles in three independent views.
- dental-comparison.json contains both transform directions, reference/source hashes, full distributions and repeat-capture checks. dental-comparison.png shows dental-to-cast distance colors.
- Upper Model 2 is explicitly labeled more chipped by the source folder; other exact chip locations/timing remain unconfirmed. The contributor reports difficulty making intact models despite experience. Damage describes the physical casts, not the actual teeth.
- The dental upper/lower bite relationship is unchanged. Casts have no measured shared bite frame and are not used as treatment-motion observations.

From repository root, with NumPy/SciPy/Open3D/Matplotlib installed:

```sh
export MPLCONFIGDIR=/private/tmp/ortho-matplotlib
PYTHONPATH=. .venv/bin/python tools/inspect_personal_casts.py datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/personal-models
OMP_NUM_THREADS=2 PYTHONPATH=. .venv/bin/python tools/compare_personal_casts.py datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/personal-models
PYTHONPATH=. .venv/bin/python datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/personal-models/build_assessment.py
```
