# Native scanner files and observed comparisons

The iOS and Android **3D scans** picker accepts exported geometry from scanner
software. These are local previews; selecting a file does not upload its bytes to
an engine or a model provider. Scanner project/session files must first be exported.

| Extension | Native preview | Supported subset |
| --- | --- | --- |
| STL | Complete mesh | Binary and ASCII; derived face normals |
| OBJ | Mesh or vertex point cloud | Positive/negative vertex indices, triangles and convex planar polygons of up to 64 vertices |
| PLY | Mesh or point cloud | ASCII, little-endian binary, big-endian binary; vertex scalar attributes and face index lists |
| ASC, XYZ | Point cloud | Whitespace-separated XYZ, optional trailing scalar attributes, `#` comments |
| PTS | Point cloud | One positive point count, followed by exactly that many XYZ records; optional trailing attributes |

OBJ textures/materials, PLY colors, and scanner intensity attributes are ignored;
no material paths are opened. OBJ curves, non-unit homogeneous vertex weights,
concave/self-intersecting/non-planar polygons, and unsupported PLY elements are
rejected. Export a triangulated mesh for those cases. Point clouds remain points;
the app does not invent a tooth surface from them. Units are not inferred.

These cover the geometry formats listed by [Revopoint's software support](https://support.revopoint3d.com/hc/en-us/articles/7777366956827-How-do-I-download-and-use-the-software)
and the [3DMakerpro Fox specifications](https://store.3dmakerpro.com/products/fox).
This is format compatibility, not validation of either scanner for dental use.
GLB/GLTF, FBX, 3MF, RSCAN/project archives, and textured scenes are not native
imports in this release. Export one of the formats above from the scanner app.

## Resource and error handling

Each file is limited to 80 MiB, one million mesh triangles or one million points,
finite coordinates within ±1,000,000 source units, and 16 KiB per text line.
Combined uploaded previews are limited to three million rendered vertices
(one million triangles total); select a single file if a pair exceeds that budget.
The four bundled sample surfaces have a separate 4.5-million-vertex budget and
are hash-checked against the history manifest. No accepted faces are sampled away.

File reads and decoding run off the UI thread. Changing sources cancels obsolete
work. Failed supported imports remain visible with an error and never silently
show USER_ONE. Unsupported extensions show an Upload error. Reset cancels iOS
reads and prevents their late results from reappearing. iOS retains at most two
scan files (160 MiB maximum raw bytes); reset the case to replace them. Android
retains URI records and reads at most two selected files for the current view.
Neither platform provides a durable scan library yet.

Only STL imports expose the existing metadata-only mobile generation path.
OBJ/PLY/point-cloud files cannot enter the STL fallback. The browser/full engine
is required for other-format review and mesh registration.

## Comparison controls

**Teeth** defaults to USER_ONE with **Both** arches: upper above, lower below.
The arches are separately positioned and fitted, not placed in a registered bite.
Select Upper or Lower to inspect one arch; drag the surface to rotate, pinch to
zoom, and Reset view to restore the camera.

Drag the continuous **Baseline → Week 7** slider to reveal the recorded week-7
surface from the right. Both observations use synchronized camera controls.
Only the rendering mask/scissor changes while dragging; files are not re-read,
meshes are not re-parsed, and vertices are never interpolated. The ends show the
complete recorded surfaces; the last 1% snaps to each exact endpoint.

There are only two observations. Cross-time registration and progress-scan units
remain unverified. A reveal comparison is not measured tooth movement, a known
intermediate visit, a treatment simulation, or a prediction. The Week 7 label is
the contributor-confirmed treatment milestone with five-day tray changes; it is
not calculated from the calendar interval between the scan export dates.

## Verification

Both native test suites consume the same 38 fixtures in `test-fixtures/scans/`,
including binary PLY in both byte orders, point clouds, OBJ negative indices,
self-intersecting polygons, invalid counts, non-finite coordinates, and truncation.
Additional tests check cancellation, bounded reads, overlong lines, exact format
metadata, and STL-only fallback. Existing tests preserve every triangle in all
four original USER_ONE scans. The iOS UI test exercises both arches, the reveal
midpoint, both endpoints, single-arch selection, and reset; Android rendering is
also checked manually on the Pixel 9 emulator.
