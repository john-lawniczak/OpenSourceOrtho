# USER_ONE — reported week 18 test scans

Published supplementary progress visit for the existing
`spec-07b7031938c84b1a9c98517b8bc4cdd3` case. The contributor's `USER_1` reference
maps to the established `USER_ONE` pseudonym; no new case identity was created.

## Original November 10 pair

**Relationship clarified November 12:** the contributor identifies
`2026-11-10-week-18-upper-test.stl`,
`2026-11-10-week-18-bottom-test.stl`, and the H4/H6 lower captures as variants
or attempts within the same reported week-18 mold/model series. They are grouped
as one visit, not successive observations of tooth movement. H4/H6 are confirmed
to share one physical lower model; the exact impression/pour/cast relationships
between the November 10 pair and those captures are not separately specified.
See `capture_relationship` in [source-metadata.json](source-metadata.json).

No intact donor surfaces have been verified and no scans have been combined.
Any later composite must preserve its source files and record which observed
surface supplied each replacement, alignment/scale evidence, and unresolved
defects. Repeated scans of a chipped cast cannot supply the missing original
surface. A new impression at a later week belongs to that later observation;
it must not be relabeled as week 18. Earlier quality reports retain their
per-file scope.

The contributor supplied an upper/lower STL pair on November 10, 2026 and
described personal scans and builds made using a stone and Play-Doh style
process: early attempts with limited quality. This description is contributor
provenance, not an independent assessment of geometric accuracy. The precise
materials, capture steps, scanner hardware, and acquisition date are unconfirmed.

**Known source-model damage:** the contributor confirms that **both** hardened
stone models were chipped and attributes the defects to poor model-making,
**not the actual teeth**. Exact chip locations and timing relative to scanning
are not separately mapped. Treat this pair as damaged-model test data, not
reference tooth geometry or evidence of tooth damage or movement.
See [quality-assessment.md](quality-assessment.md) for the mesh evaluation,
[mesh-quality.json](mesh-quality.json) for reproducible counts, and
[mesh-views.png](mesh-views.png) for independent surface views. Geometry checks
cannot reconstruct the undamaged stone or confirm the original tooth surfaces.

The source filenames carry `2026-11-10` and `week-18`. Week 18 is the reported
progress label, not a verified tray number or 18 elapsed calendar weeks. Progress
sequence 2 means the second contributed progress visit after the published week 7
pair. It does not overwrite or relabel the earlier scans.

| File | Arch | Source filename |
| --- | --- | --- |
| `progress-02-upper.stl` | Maxillary | `2026-11-10-week-18-upper-test.stl` |
| `progress-02-lower.stl` | Mandibular | `2026-11-10-week-18-bottom-test.stl` |

Both files preserve every source byte. `manifest.json` records CLI-inspected
hashes, geometry counts, and bounds for this visit only. `source-metadata.json`
records the source mapping, reported timing, and publication scope. The STL
headers identify JMStudio v2.4.19.0131; they do not identify scanner hardware.

Scale, upper/lower alignment, cross-time registration, and surface fidelity remain
unverified. No tooth movement, tracking error, or treatment outcome is inferred.
These are research inputs for the clear-aligner planning safety playground and
research toolkit.

The contributor authorized public redistribution of this visit, its scans and
chipped-model metadata on November 12, 2026. The case-root `consent.json` lists
each approved asset. This bundle moved from `private/` to `visits/`; scan bytes
are unchanged. Earlier private contribution records remain as provenance in
`prior_sharing_scope`. Other private contributions are not authorized by this change.

## Additional lower captures contributed November 12

Both additional mandibular captures belong to the same reported week 18 visit;
neither replaces the original pair or the other capture.

| Capture | Original file | Manifest | Source metadata |
| --- | --- | --- | --- |
| Fusion H4 | [2026-11-12_USER_ONE_lower_week-18_fusion-h-4.stl](captures/fusion-h-4/2026-11-12_USER_ONE_lower_week-18_fusion-h-4.stl) | [Manifest](captures/fusion-h-4/manifest.json) | [Provenance](captures/fusion-h-4/source-metadata.json) |
| Fusion H6 | [2026-11-12_USER_ONE_lower_week-18_fusion-h-6.stl](captures/fusion-h-6/2026-11-12_USER_ONE_lower_week-18_fusion-h-6.stl) | [Manifest](captures/fusion-h-6/manifest.json) | [Provenance](captures/fusion-h-6/source-metadata.json) |

The additional captures have a separate [comparative evaluation](captures/quality-assessment.md),
[topology inventory](captures/mesh-quality.json), and
[surface views](captures/mesh-views.png). H4 contains 581,144 triangles; H6 contains
587,840. Both preserve every source byte. Acquisition date, scale, capture method,
and anatomical registration remain unverified for both. The contributor confirms
H4 and H6 share the same physical lower model, with a small chip on an unidentified
front tooth. The chip location, timing, and any repair/trimming history are not
yet mapped. This reports model damage, not actual tooth damage.

Both binary STLs have valid declared record lengths and no non-finite face
records. H4 is 29,057,284 bytes; H6 is 29,392,084 bytes. These are file checks,
not a surface-fidelity assessment. November 12 in the filenames is the
contribution/filing date, not a verified acquisition date. The original pair's
damage report, topology inventory, and views do not assess these
captures; those artifacts and their reproduction script retain their original
two-scan scope.

Both additional captures are included in the public asset allowlist and catalog. No movement fit or preview is regenerated by this
data addition.
