# Public source snapshot — 2026-09-22

The maintainer authorized publishing a clean version of the completed changes to
`john-lawniczak/OpenSourceOrtho`. This snapshot updates the existing public `main`
with one commit based on its previous tip, preserving public history while
keeping private development commits out of the public ancestry.

## Included

- iOS and Android 0.4.0 (build 4), complete real scan rendering, both arches,
  continuous baseline/week-7 reveal, and STL/OBJ/PLY/ASC/XYZ/PTS local imports.
- The stable USER_ONE UUID dataset with all four original baseline/week-7 STLs,
  authorized source views, redacted metadata, provenance, and quality limitations.
- Browser intake and workflow updates, catalog organization, regression tests,
  native CI, complete license notices, and current build/audit documentation.

The sample geometry is permanently tracked in Git and copied into both mobile
apps at build time. It remains pseudonymous rather than anonymous. Exact dates
and geometry are retained under the existing contribution instructions; this
publication does not expand the contribution's consent scope.

## Excluded and retained history

- The third-party reference simulation: redistribution rights are unverified.
  Only its provenance metadata and explicitly qualified derived observations are
  included; their references do not imply an available video download.
- Private maintainer `TODO.md`, ignored development logs, local workflows/caches,
  raw CBCT/DICOM, identifying paperwork, and dataset assets outside the explicit
  `consent.json` publication allowlist.

The project's own UI demo remains included. Existing public history already
contains older copies of the reference video and working notes. This update
removes them from the current tree; it does not erase historical copies or
rewrite public branches. No new private development ancestry is published.

## Verification and boundaries

Both native CI jobs passed on the development candidate. Its validation includes
19 Swift tests, 19 Android JVM tests, iOS UI tests, Android emulator checks,
668 Python tests, 124 JavaScript tests, lint, catalog, and maintainability checks.
The clean snapshot separately passed 668 Python tests (2 optional-backend skips),
124 JavaScript tests, and 14 browser end-to-end tests. Publication-scope checks,
all four original STL hashes, tracked-file/credential-pattern checks, generated
catalog consistency, Ruff, strict maintainability, and Git whitespace checks
also passed. Native source and resources match the CI-verified candidate.

The [mobile audit](MOBILE_AUDIT_2026-09-22.md) records remaining physical-device,
registration, and importer-coverage risks. The slider reveals two observations;
it does not measure or simulate tooth movement. This is a source publication,
not an app-store release, deployment, or assurance of physical-use safety.
