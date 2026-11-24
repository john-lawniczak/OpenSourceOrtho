# Longitudinal accuracy benchmark

Run `python tools/benchmark_motion.py manifest.json --output report.json` with the
`motion-preview` extra installed. The manifest lists `cases`, each with a
`case_id`, `prediction` JSON path and independent `truth` JSON path relative to
the manifest. Keep identifiable records and review packets in ignored local storage.

Truth schema `ortho-motion-truth-v1` declares the prediction's coordinate `frame`,
ordered endpoint `source_hashes`, `units`, and `kind` (`synthetic`, `reviewed-real`,
or `reviewed-repeat`). Real cases require a `review` object with a reviewer and
explicit `boundaries`, `correspondence`, and `poses` review flags. Each truth tooth
has `tooth`, `target_tooth`, `pivot`, `translation`, and `quaternion_xyzw`.
`source_face_tooth_ids` and `target_face_tooth_ids` are face-order FDI arrays
(0 denotes context). Repeat cases specify `translation_tolerance` and
`rotation_tolerance_deg`; tolerances are benchmark settings, not treatment limits.

The report separates boundary accuracy, identity errors from independent target
face labels, translation RMSE at common pivots, rotation error, false motion in
repeat scans, and missing fits. Missing fits never count as zero error. Missing
target face evidence yields an unavailable identity score, never self-validation
from the algorithm's assigned FDI label. Predictions need `target_faces` per region
to score identity. Synthetic and reviewed-real results remain separate.

Current status: executable scoring and controlled zero-motion/error-injection tests
are available. On November 15, 2026 the contributor confirmed the H4/H6 physical
model was unchanged between captures, with the chip already present in both.
Reviewed regions and a reproducible capture-consistency report remain pending.
Independently reviewed USER_ONE boundary/pose/correspondence labels remain missing.
See [the H4/H6 review steps](LOCAL_RESEARCH_WORKFLOWS.md#prepare-an-h4h6-repeatability-check).
Existing input validation statements
and the root/bone engineering fixture do not substitute for that benchmark truth.
The Desktop IMGDATA CBCT is locally accessible: 825 DICOM objects, including an
824-slice 900×900 primary stack at 0.2 mm spacing. Its ignored local pointer has
been repaired; raw identifiers and pixels remain outside Git. A baseline CBCT can supply anatomy and a registration reference
once accessible, segmented, and reviewed; it cannot establish later weekly positions.

**External data source, cleared for use, but not independent motion truth
(verified November 2026)**: a Zenodo record (DOI 10.5281/zenodo.11280343, CC
BY 4.0, open download, no access gate) publishes weekly STL scans across two
patients' full clear-aligner treatments (T0 through T10), including planned
aligner-cut surfaces and per-tooth crown meshes. Its companion peer-reviewed
paper (Filippon et al., *Oral* 2024, 4(4), 487-504, DOI 10.3390/oral4040039)
confirms ethics committee approval was appropriately waived under Swiss
guidelines for a two-patient case study, written informed consent was
obtained from both patients, and its Data Availability Statement names this
exact Zenodo record. CC BY 4.0 permits commercial use and derivatives; citing
that paper is required (attribution).

Checked the authors' own analysis code
(github.com/unibas-bmc/toothMovementAnalysis): the per-tooth crown mesh at
each visit is **not independently segmented or reviewed at that visit**. A
human segmented teeth once, at the final visit; the authors' own pipeline
(non-rigid ICP, then a rigid fit per tooth) propagates that single
segmentation backward to every earlier visit. So the per-visit tooth
positions here are the *output of a specific published registration
algorithm*, not independently measured ground truth. Using them as this
benchmark's `reviewed-real` truth would mean comparing our pipeline against
another automated method's answer, not against verified reality - a real but
more modest form of validation (cross-method agreement), not a substitute for
an independently reviewed case. The one human-labeled timepoint (the final
visit's crown segmentation) remains a legitimate independently-reviewed
boundary label for two more real people, useful for segmentation-benchmark
work, separately from any motion claim. Caveats: n=2; three of six authors
disclose ties to the company that supplied the study's aligners (Bottmedical
AG) - noted for transparency, not a licensing or consent issue.
