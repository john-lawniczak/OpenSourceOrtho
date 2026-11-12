# Release readiness review — 2026-09-21

**Publication update — 2026-09-22:** The maintainer authorized a clean public
snapshot of the completed updates. The [publication record](PUBLIC_RELEASE_2026-09-22.md)
documents its scope, exclusions, validation, and unchanged history. The
[mobile implementation audit](MOBILE_AUDIT_2026-09-22.md) supersedes the viewer
behavior and native validation counts below. The earlier private-publication hold
has been lifted for this source snapshot; app-store delivery remains separate.

## Changes ready for review

- Both mobile Teeth tabs default to USER_ONE's complete baseline scan. Baseline /
  Week 7 and Upper / Lower select the four actual recorded surfaces. Native
  rotation, zoom, reset, depth testing, and lighting replace synthetic teeth and
  the fabricated 12-stage slider. Imported scans remain separate from the sample.
- The previous iOS parser sampled/truncated faces; Android displayed only the
  first 14,000 faces per arch. Both now preserve every face, reject malformed
  coordinates, cap mobile resource use, and cancel superseded parsing work.
- Build phases copy only the four original STLs from the UUID dataset and verify
  their hashes when loading. Removed six redundant legacy mobile STL resources
  (about 62 MB from the current source tree; Git history is unchanged).
- Rendering and parsing have their own modules. The legacy mobile screen budgets
  were reduced from 1,255 to 806 lines (iOS) and 1,321 to 934 (Android).
- Repository-wide Ruff errors were resolved, including explicit preservation of
  public printing re-exports. Native CI now builds/tests both apps; Python CI
  checks lint and the generated catalog.
- Added the complete Apache-2.0 license, preserved project attribution in NOTICE,
  and added the full upstream Three.js r169 MIT permission notice. Removed the
  public README's link to an intentionally ignored local TODO file.

See the [mobile behavior and build notes](../mobile/README.md),
[iOS screenshot](images/mobile-ios-real-scans.png), and
[Android screenshot](images/mobile-android-real-scans.png).

## Validation and audit scope

The review covers current source, tracked-file hygiene, dataset provenance and
publication boundaries, native app resources, CI, dependency notices, installed
Python dependency advisories, regression tests, and simulator/emulator rendering.
It is not an exhaustive security audit or a verification of treatment outcomes.

- Python regression suite: 668 passed, 2 optional-backend skips.
- JavaScript: 124 passed; browser end-to-end suite: 14 passed.
- Swift core: 15 passed; Android core: 15 passed. Both parse all four originals and
  assert the exact full face counts, not a sampled subset.
- iOS simulator UI test: all four visits/arches render, counts match, and sample
  viewing exposes neither a fabricated stage slider nor plan generation.
- Android Pixel 9 emulator: baseline/week-7 and upper/lower selection, rotation,
  and rendering visually checked. This is separate from JVM parser coverage.
- iOS simulator build and Android debug build pass. Packaged STL bytes are
  compared against the dataset's SHA-256 manifest.
- Android lint passes with warnings: existing target-SDK/dependency currency,
  icon/layout tooling, and allocations in the schematic tooth-number map. These
  are not a completed store-release review.
- Ruff, strict maintainability, generated catalog, and Git whitespace checks pass.
- Current tracked files contain no raw DICOM, private `.local` records, signing
  keys, or matches for the checked private-key/GitHub/OpenAI/AWS credential
  patterns. This pattern check does not establish that all historical data is
  anonymous or that every possible secret format was searched.
- `pip-audit` checked all 17 installed Python packages (excluding this editable
  project). The initial check flagged local pip 24.0 and setuptools 79.0.1. After
  upgrading the local tools to pip 26.2.1 and setuptools 84.0.0, no known advisories
  were reported. Those virtual-environment updates are not committed dependency
  pins. Optional uninstalled providers/backends and native dependency CVEs were
  not covered by that Python advisory check.

## Publication disposition

1. The reference video with unverified redistribution rights is omitted from the
   public snapshot. Metadata marks it unavailable. Original geometry, authorized
   source renderings, and case metadata remain within the existing consent scope.
2. USER_ONE is pseudonymous, not anonymous. Original dental geometry and exact
   case dates retain their identifying potential; no raw CBCT or identifying
   paperwork is included in this snapshot.
3. Publication is a single snapshot commit on the existing public `main`, with
   no private development commits added as ancestors. Existing public history
   still contains older versions of the omitted files; no history rewrite,
   force push, mirror push, tag, app-store release, or deployment is part of this
   publication.

## Remaining product limits

The apps render whole-arch surfaces, not segmented tooth movement. Each view is
independently fitted; progress units and cross-time/bite registration remain
unverified. The original scan quality and unknowns are documented in
[USER_ONE's record](../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/outcome-notes.md).

Native uploads still pass metadata to the generation endpoint; mesh registration,
durable review storage, production endpoints/signing, store requirements, and
real-device performance across supported hardware remain unfinished. The local
Python HTTP server defaults to loopback and has no deployment authentication;
it must not be treated as a production patient-data service. The 80 MiB / one
million triangle mobile cap is an explicit resource limit, not a quality claim.
