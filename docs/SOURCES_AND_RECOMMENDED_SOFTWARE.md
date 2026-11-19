# Sources and Recommended Software

This file is the living source ledger for OpenSource Ortho. Use it to track external references, license posture, implementation ideas, and changes that may affect product direction.

Last recorded source review: 2026-11-19.

## How To Use This File

- Recheck sources before adopting a library, model, dataset, workflow, or treatment heuristic.
- Treat commercial products as references only unless a clear permissive license exists.
- Record the date reviewed when a source affects implementation.
- Watch for license changes, deprecations, regulatory notes, model-weight restrictions, and new open-source alternatives.
- Update [OPEN_SOURCE_REFERENCES.md](OPEN_SOURCE_REFERENCES.md), [ARCHITECTURE.md](ARCHITECTURE.md), or [SAFETY.md](SAFETY.md) when source changes alter project assumptions.

## Sources Checked

| Source | URL | Current Use | Watch For |
| --- | --- | --- | --- |
| BlueSkyPlan download/license language | https://www.blueskybio.digital/page/download-software | Proprietary/freeware cautionary reference only. Do not fork or copy. | License terms, any explicit OSI-approved source license, product workflow changes. |
| 3D Slicer license/commercial-use notes | https://slicer.readthedocs.io/en/5.10/user_guide/about.html | License/regulatory reference for a possible host platform. | License notes, medical-device disclaimers, extension guidance. |
| 3D Slicer platform | https://www.slicer.org/ | Open-source platform reference for imaging, segmentation, and possible extension hosting. | Platform roadmap, extension APIs, segmentation and DICOM workflows. |
| SlicerCMF | https://cmf.slicer.org/ | Dental/craniofacial workflow reference inside 3D Slicer. | Extension status, algorithms, dependency/license updates. |
| Open3D MIT note | https://www.open3d.org/ | Optional `mesh-processing` dependency for local geometry/segmentation experiments. | License, Python API changes, mesh registration and visualization features. |
| PyVista MIT note | https://pyvista.org/ | Candidate Python visualization layer. | License, VTK compatibility, web/desktop rendering options. |
| VTK BSD-3-Clause note | https://github.com/Kitware/VTK | Mature scientific visualization backend reference/dependency. | License, Python packaging, rendering features. |
| pydicom MIT license | https://github.com/pydicom/pydicom/blob/main/LICENSE | Optional `dicom` extra for local CBCT/DICOM structural metadata parsing. | License, API changes, DICOM parsing/security guidance. |
| Clear aligner staging reference | https://pmc.ncbi.nlm.nih.gov/articles/PMC8388591/ | Literature reference for conservative movement-cap heuristics. | Updated literature, movement efficacy estimates, limitations. |
| Clear aligner staging reference | https://www.mdpi.com/2076-3417/14/15/6690 | Literature reference for movement planning and aligner biomechanics. | Updated review data, staging recommendations, limitations. |
| Teeth3DS+ / 3DTeethSeg'22 dataset | https://3dteethseg.grand-challenge.org/ | Re-confirmed CC BY-NC-ND 4.0 (non-commercial, no derivatives). Not usable for training a shipped crown-segmentation model. | Any commercial licensing offer from the dataset owner; new license-clear alternatives. |
| ToothFairy2 CBCT dataset | https://ditto.ing.unimore.it/toothfairy2/ | Confirmed CC BY-NC-SA 4.0, account-gated download. Not usable for training a shipped CBCT segmentation model. | Future ToothFairy releases changing NC terms. |
| DENTEX panoramic dataset | https://huggingface.co/datasets/ibrahimhamamci/DENTEX | License conflict: originating arXiv paper states CC-BY, current maintained dataset card states CC-BY-NC-SA. Treat as NOT usable until resolved directly with current maintainers. | Dataset card updates resolving the conflict. |
| Aligner tooth-movement dataset (2 patients) | https://zenodo.org/records/11280343 (DOI 10.5281/zenodo.11280343) | **Cleared for use (verified 2026-11-19).** CC BY 4.0, open download. Companion paper (Filippon et al., *Oral* 2024, DOI 10.3390/oral4040039) confirms IRB approval waived under Swiss guidelines for a 2-patient case study, written informed consent obtained from both patients, and the paper's own Data Availability Statement names this Zenodo record. CC BY requires attribution/citation on use. In use as a candidate external "reviewed-real" truth source for `MOTION_BENCHMARK.md`. | Cohort growing beyond 2 patients; any future restriction added to the Zenodo record. |

## Recommended Software To Evaluate

### Mesh and Geometry

Open3D

- Use for point-cloud and mesh processing, registration experiments, geometry utilities, and potential segmentation prototypes.
- Good fit for Python-first research tooling; available as the optional `mesh-processing` extra.

trimesh

- Use for STL/OBJ loading, transforms, mesh measurements, repair helpers, bounds, and simple geometry operations.
- Add only after checking the current license and dependency footprint.

PyVista / VTK

- Use for early Python 3D visualization, mesh inspection, and possible desktop prototype views.
- Keep rendering adapters separate from `orthoplan/model` and `orthoplan/planning`.

### Medical Imaging and Dental Workflows

3D Slicer

- Use as a reference or optional host for CBCT/DICOM-heavy workflows.
- Strong candidate for future extension work, but not the initial dependency path.

SlicerCMF

- Use as a dental/craniofacial workflow reference.
- Study interaction patterns and data flow, not proprietary treatment claims.

pydicom

- Use for local DICOM/CBCT structural metadata parsing only; keep pixel bytes out
  of plan JSON.
- Keep DICOM IO in `orthoplan/io` / `orthoplan.dicom_intake` and preserve the
  `stop_before_pixels=True` pattern.

### Commercial Workflow References

BlueSkyPlan

- Reference only.
- Free availability is not enough; do not treat it as open source without a permissive source license.

Commercial Clear-Aligner Plan Editors

- Reference only.
- Useful for understanding expectations around staged tooth visualization, setup
  comparison, doctor review, direct 3D controls, live restaging, and patient
  communication.
- Describe learned workflow ideas in generic language.

## Monitoring Cadence

Recheck these sources when:

- adding or upgrading dependencies
- changing movement-cap defaults
- adding CBCT/DICOM support
- adding segmentation models or model weights
- designing a new visualization workflow
- preparing a public release
- changing licensing or commercialization plans
