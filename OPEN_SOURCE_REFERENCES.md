# Open-Source and Commercial References

This project should compose from permissively licensed open-source libraries and use commercial products only as workflow references.

## Do Not Fork Or Copy

BlueSkyPlan is marketed as free dental planning software, but free does not mean open source. Its download page requires agreement to terms and a license agreement. Treat it as proprietary unless a clear OSI-approved source license is found.

ClinCheck is Align Technology/Invisalign treatment-planning software. It is useful as a workflow reference for stage visualization, doctor review, plan modification, and patient-facing progress display. Do not copy UI, assets, source, private workflows, or proprietary terminology beyond nominative reference.

## Good Open-Source Building Blocks

3D Slicer

- BSD-style open-source platform
- useful as a reference host for medical imaging, segmentation, registration, and CBCT workflows
- not FDA-approved by default, so its own docs reinforce a similar regulatory boundary

SlicerCMF

- 3D Slicer extension for dental and craniofacial image analysis
- useful reference for dental imaging workflow, registration, segmentation, and quantification

Open3D

- MIT-licensed 3D data processing library
- useful for point clouds, meshes, registration, visualization, and geometry utilities

PyVista / VTK

- PyVista is MIT-licensed and wraps VTK-style 3D visualization in Pythonic APIs
- VTK is BSD-3-Clause and mature for scientific visualization
- useful for desktop research prototypes and mesh inspection

pydicom

- MIT-licensed Python DICOM library
- useful only if CBCT/DICOM support is added

trimesh

- permissive mesh-processing library
- useful for STL/OBJ loading, mesh transforms, bounds, normals, measurements, and repair workflows

DentalSegmentator / Slicer dental AI extensions

- promising references for CBCT segmentation workflows
- every model, weight file, and dataset license must be checked before use
- research and medical AI tools may have non-commercial, dataset, or model-weight restrictions even when code is visible

MeshLab / CloudCompare

- useful references for mesh inspection and repair workflows
- watch licenses carefully if embedding or linking; prefer them as external tools unless license review is complete

## Source Links To Recheck During Implementation

- BlueSkyPlan download/license page: https://www.blueskybio.digital/page/download-software
- ClinCheck Pro overview: https://www.invisalign.com/provider/align-digital-platform/clincheck
- 3D Slicer: https://www.slicer.org/
- 3D Slicer license docs: https://slicer.readthedocs.io/en/5.10/user_guide/about.html
- SlicerCMF: https://cmf.slicer.org/
- Open3D: https://www.open3d.org/
- PyVista: https://pyvista.org/
- VTK: https://github.com/Kitware/VTK
- pydicom: https://github.com/pydicom/pydicom

