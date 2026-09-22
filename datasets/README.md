# Published research datasets

Start here to browse contributed cases. Each UUID folder is the source of truth
for one longitudinal case; a pseudonym is a readable label, not a person's name.
The UUID is preserved across visits. No real-identity lookup is published.

| Pseudonym | Specimen ID | Available scans | Scan pairs | CBCT metadata |
| --- | --- | --- | ---: | --- |
| [USER_ONE](spec-07b7031938c84b1a9c98517b8bc4cdd3/README.md) | `spec-07b7031938c84b1a9c98517b8bc4cdd3` | initial, progress | 2 | Redacted metadata only |

## Layout and publication

- `manifest.json` owns identity, pseudonym, scan roles, hashes, and summary metadata.
- `consent.json` records publication scope and any exact-date retention exception.
- Original STL files keep standard role/arch labels at the case root.
- `media/` contains source renderings and reference media with their provenance.
- `derived/` contains regenerable comparisons, topology reports, and transcriptions.
- `fixtures/` contains engineering fixtures, not measured patient anatomy.
- `.local/` is ignored and never served; raw CBCT and private records stay there.

Pseudonyms and UUIDs do not establish anonymity. Case dates remain only where
their retention was explicitly requested. Existing reference-media rights caveats
remain in force; a publication record does not create new permissions.

The development server serves only paths listed in each case's `public_assets`
and rejects traversal and symlinks. Private files do not become public by being
placed inside a case folder. The catalog lists no acquisition dates or identities.

## Add or update a case

Follow [DATA_CONTRIBUTION.md](../docs/DATA_CONTRIBUTION.md). Keep the existing
UUID for later visits and append progress records instead of replacing originals.
After reviewing the manifest, pseudonym, scope, and files, regenerate this table
and `index.json` with `python3 tools/build_dataset_catalog.py`.
Use `--check` to verify generated outputs without modifying files.

Original scans remain in Git; this reorganization does not decimate files, rewrite
history, or introduce LFS. Apps package derived previews from the canonical cases.
This is a clear-aligner planning safety playground and research toolkit.
