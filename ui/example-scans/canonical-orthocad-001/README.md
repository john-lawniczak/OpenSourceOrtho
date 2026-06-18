Canonical OrthoCAD scan fixture used by the browser UI.

Files:
- `sample-test-case-upper.stl`: maxillary occlusion shell
- `sample-test-case-lower.stl`: mandibular occlusion shell
- `sample-test-case-cliniccheck-reference.mp4`: cropped/debranded reference
  simulation associated with the same source STL pair
- `reference-media.json`: non-clinical metadata for the reference video
- `source-export-metadata.json`: redacted source-export metadata showing that
  the sample STLs correspond to the iTero `shell_occlusion` upper/lower jaw
  surfaces, with no separate bite STL present in the local export

These STLs are whole-arch scan shells, not segmented per-tooth meshes. They are
the exact models used by the in-app **Sample Test Case** (and named to match it).
The UI uses them to verify exact scan rendering and camera/material behavior. The
Sample Test Case pairs these scans with a simulated educational stage sequence;
it does not represent a clinical prediction, diagnosis, or treatment plan.

The reference video is retained only as comparison material for the sample case.
It is not an outcome record, not a treatment approval, and not evidence that the
sample educational stage sequence is clinically correct. Confirm redistribution
rights before sharing the media outside a private/local dataset.
