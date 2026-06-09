# Open-Source and Commercial References

This project should compose from permissively licensed open-source libraries and use commercial products only as workflow references.

For the living source ledger and monitoring cadence, see [SOURCES_AND_RECOMMENDED_SOFTWARE.md](SOURCES_AND_RECOMMENDED_SOFTWARE.md).

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
- useful for point clouds, meshes, registration, visualization, geometry utilities, and local segmentation experiments
- available as the optional `mesh-processing` extra; the core app still has a pure-Python segmentation baseline

PyVista / VTK

- PyVista is MIT-licensed and wraps VTK-style 3D visualization in Pythonic APIs
- VTK is BSD-3-Clause and mature for scientific visualization
- useful for desktop research prototypes and mesh inspection

pydicom

- MIT-licensed Python DICOM library
- candidate optional dependency for the planned CBCT/DICOM ingestion milestone

Three.js

- MIT-licensed WebGL 3D library
- used by the browser UI's 3D progress viewer; vendored pinned (r169) under `ui/vendor/` and loaded via an import map so the app runs offline with no runtime CDN calls
- renders abstract proxy geometry only (we never serve scanned mesh bytes)

trimesh

- permissive mesh-processing library
- useful for STL/OBJ loading, mesh transforms, bounds, normals, measurements, and repair workflows
- available as an optional `mesh` extra; current code only uses it opportunistically for quality metadata when installed

DentalSegmentator / Slicer dental AI extensions

- promising references for CBCT segmentation workflows
- every model, weight file, and dataset license must be checked before use
- research and medical AI tools may have non-commercial, dataset, or model-weight restrictions even when code is visible

MeshLab / CloudCompare

- useful references for mesh inspection and repair workflows
- watch licenses carefully if embedding or linking; prefer them as external tools unless license review is complete

## License Traps To Watch

- **Separate three licenses for any AI tool**: code license, model-weight license, and dataset
  license are often different. Code can be MIT while weights/datasets are CC-BY-NC or carry a
  research-only EULA. Check all three before using DentalSegmentator or any segmentation model.
- **3D Slicer ecosystem copyleft**: Slicer core is BSD, but individual extensions and some
  bundled components are GPL. Distributing a Slicer extension can pull copyleft obligations into
  anything linked with it.
- **trimesh optional backends**: trimesh itself is MIT, but optional acceleration/format backends
  it can pull in carry varied licenses. Pin and audit only the backends actually imported.
- **Trademarks**: "Invisalign", "ClinCheck", and "SmartTrack" are trademarks. Use them only as
  nominative references in prose, never in code identifiers, UI labels, or product naming.
- **Sample datasets**: STL/CBCT sample scans often carry patient-consent or dataset licenses.
  Phase 1 uses synthetic fixtures only; do not check in third-party patient scans.

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
