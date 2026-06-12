# Sources and Recommended Software

This file is the living source ledger for OpenSource Ortho. Use it to track external references, license posture, implementation ideas, and changes that may affect product direction.

Last recorded source review: 2026-06-04.

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
| ClinCheck Pro | https://www.invisalign.com/provider/align-digital-platform/clincheck | Commercial workflow reference for review, staging, visualization, and provider handoff. | Proprietary terminology, UI/workflow changes, feature ideas to describe generically. |
| 3D Slicer license/commercial-use notes | https://slicer.readthedocs.io/en/5.10/user_guide/about.html | License/regulatory reference for a possible host platform. | License notes, medical-device disclaimers, extension guidance. |
| 3D Slicer platform | https://www.slicer.org/ | Open-source platform reference for imaging, segmentation, and possible extension hosting. | Platform roadmap, extension APIs, segmentation and DICOM workflows. |
| SlicerCMF | https://cmf.slicer.org/ | Dental/craniofacial workflow reference inside 3D Slicer. | Extension status, algorithms, dependency/license updates. |
| Open3D MIT note | https://www.open3d.org/ | Optional `mesh-processing` dependency for local geometry/segmentation experiments. | License, Python API changes, mesh registration and visualization features. |
| PyVista MIT note | https://pyvista.org/ | Candidate Python visualization layer. | License, VTK compatibility, web/desktop rendering options. |
| VTK BSD-3-Clause note | https://github.com/Kitware/VTK | Mature scientific visualization backend reference/dependency. | License, Python packaging, rendering features. |
| pydicom MIT license | https://github.com/pydicom/pydicom/blob/main/LICENSE | Candidate optional dependency for planned CBCT/DICOM ingestion. | License, API changes, DICOM parsing/security guidance. |
| Clear aligner staging reference | https://pmc.ncbi.nlm.nih.gov/articles/PMC8388591/ | Literature reference for conservative movement-cap heuristics. | Updated literature, movement efficacy estimates, limitations. |
| Clear aligner staging reference | https://www.mdpi.com/2076-3417/14/15/6690 | Literature reference for movement planning and aligner biomechanics. | Updated review data, staging recommendations, limitations. |

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

- Use when DICOM/CBCT import enters the contract-and-ingestion milestone.
- Keep DICOM IO in `orthoplan/io`.

### Commercial Workflow References

BlueSkyPlan

- Reference only.
- Free availability is not enough; do not treat it as open source without a permissive source license.

ClinCheck Pro

- Reference only.
- Useful for understanding expectations around staged tooth visualization, doctor review, and patient communication.
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
