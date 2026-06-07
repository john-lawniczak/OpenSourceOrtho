Canonical OrthoCAD scan fixture used by the browser UI.

Files:
- `sample-test-case-upper.stl`: maxillary occlusion shell
- `sample-test-case-lower.stl`: mandibular occlusion shell

These STLs are whole-arch scan shells, not segmented per-tooth meshes. They are
the exact models used by the in-app **Sample Test Case** (and named to match it).
The UI uses them to verify exact scan rendering and camera/material behavior. The
Sample Test Case pairs these scans with a simulated educational stage sequence;
it does not represent a clinical prediction, diagnosis, or treatment plan.
