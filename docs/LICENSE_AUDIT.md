# Dependency License Audit

> Dependency table reviewed: 2026-06-04. License notices completed: 2026-09-21. Versions are those observed during the review;
> actual versions float within the `pyproject.toml` constraints. Re-run the
> audit when adding or bumping a dependency (see CONTRIBUTING.md).

**Project license:** AGPL-3.0-only (GNU Affero General Public License, version 3 only).
License transition recorded: 2026-11-22; dependency versions below were not re-audited.

All dependencies below are permissive (MIT / BSD / Apache-2.0 / PSF). Their
licenses are compatible with the project as a whole being distributed under
AGPLv3; their own terms and notices continue to apply to their code. There are
no copyleft dependencies in this table; the project itself is now copyleft.
Previously Apache-covered project portions retain their terms in
[LICENSES/Apache-2.0.txt](../LICENSES/Apache-2.0.txt).

## Runtime (installed by default)

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| pydantic | 2.13 | MIT | data models |
| pydantic-core | 2.46 | MIT | transitive (pydantic) |
| typing-extensions | 4.15 | PSF-2.0 | |
| annotated-types | 0.7 | MIT | transitive (pydantic) |

## Dev extra (`.[dev]`)

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| pytest | 9.0 | MIT | |
| ruff | 0.15 | MIT | linter |
| iniconfig | 2.3 | MIT | transitive (pytest) |
| pluggy | 1.6 | MIT | transitive (pytest) |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | transitive (pytest) |

## Optional extras

| Extra | Package | Version | License | Notes |
|-------|---------|---------|---------|-------|
| `providers` | openai | 2.41 | Apache-2.0 | advisory layer only |
| `mesh` | trimesh | 4.x | MIT | optional mesh quality metadata |
| `mesh-processing` | open3d | 0.x | MIT | optional local mesh-processing backend for segmentation experiments |
| `e2e` | playwright | 1.60 | Apache-2.0 | headless test only |
| `e2e` | pyee | 13.0 | MIT | transitive (playwright) |
| `e2e` | greenlet | 3.5 | MIT AND PSF-2.0 | transitive (playwright) |

The Playwright **Chromium** binary downloaded for the e2e test is a build/CI
tool only; it is not redistributed as part of this package. Chromium itself is
BSD-3-Clause with additional component licenses.

## Vendored frontend (committed under `ui/vendor/`)

| File | Source | Version | License |
|------|--------|---------|---------|
| `three.module.js` | Three.js | r169 | MIT |
| `OrbitControls.js` | Three.js examples | r169 | MIT |

Three.js is vendored (not fetched from a CDN at runtime) so the UI works
offline. The upstream header is retained in `three.module.js`, and the full r169 MIT
permission notice is now included in [`ui/vendor/LICENSE.three`](../ui/vendor/LICENSE.three).
Keep both notices and bump both files together. The root LICENSE contains the
complete GNU AGPLv3 terms, with project attribution and prior-license notices
in NOTICE. Sources:
[Three.js r169 license](https://github.com/mrdoob/three.js/blob/r169/LICENSE) and
[GNU AGPLv3 text](https://www.gnu.org/licenses/agpl-3.0.html).

## Traps watched (see OPEN_SOURCE_REFERENCES.md)

- AI/segmentation tools: code, model-weight, and dataset licenses are separate —
  none are currently a dependency.
- 3D Slicer extensions can carry GPL — not a dependency; referenced only.
- Blender and PyMeshLab/MeshLab are GPL — keep them as external workflow tools
  unless the project intentionally accepts GPL obligations.
- Commercial product trademarks: nominative reference only, never
  in code identifiers or UI labels.

## Restricted dataset access update (2026-11-23)

The Tsinghua / Beijing Stomatological Hospital paired-model dataset remains
unimported and excluded from project imports and shipped models/artifacts under
current terms. The access response requires an authorized institutional
representative to sign and prohibits downstream commercial reuse. No separate
permission for weights, aggregate statistics or derived transforms is established.
The project's AGPL license does not supply missing third-party data rights. See
the [source ledger](SOURCES_AND_RECOMMENDED_SOFTWARE.md) for provenance and
reconsideration conditions.
