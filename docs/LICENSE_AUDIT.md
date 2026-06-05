# Dependency License Audit

> Last reviewed: 2026-06-04. Versions are those observed during the review;
> actual versions float within the `pyproject.toml` constraints. Re-run the
> audit when adding or bumping a dependency (see CONTRIBUTING.md).

**Project license:** Apache-2.0.

All dependencies below are permissive (MIT / BSD / Apache-2.0 / PSF) and
compatible with distributing this project under Apache-2.0. There are no
copyleft (GPL/LGPL) dependencies.

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
offline. The upstream MIT license header is retained in `three.module.js`; keep
it intact on any version bump, and bump both files together to a matching
release.

## Traps watched (see OPEN_SOURCE_REFERENCES.md)

- AI/segmentation tools: code, model-weight, and dataset licenses are separate —
  none are currently a dependency.
- 3D Slicer extensions can carry GPL — not a dependency; referenced only.
- Trademarks (Invisalign/ClinCheck/SmartTrack): nominative reference only, never
  in code identifiers or UI labels.
