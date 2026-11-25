# Post-implementation audit — November 25, 2026

Scope: all changes applied on November 25, including capture provenance, upper and
lower impression ingestion, same-condition photographs, and their public release
in PR #10. Review also covered nearby asset resolution, finding lint, benchmark
discovery, CLI output handling, and companion rendering. This is a software audit
of the research toolkit, not validation of anatomical accuracy or physical use.

## Findings and fixes

| Priority | Concrete issue and impact | Applied fix and regression evidence |
| --- | --- | --- |
| P1 | `review-captures --out` compared resolved paths only. A differently named hard link to the manifest or scan passed the guard; `write_text` then truncated the source inode. This could destroy original evidence. | Reject output files sharing a source inode and write via a temporary sibling followed by atomic replacement. Tests reproduce both source-hard-link cases and verify that replacing a report leaves its other hard links untouched. Input hashing now streams. |
| P2 | One malformed index, summary, or rejected finding raised through the combined companion API, hiding otherwise valid casts and impressions. Bad photo metadata could also hide its scan. | Isolate expected record-read/validation errors per bundle and photo. Return a generic `issues` notice without exception text or local paths; keep independent records. Direct downloads retain hash, consent and finding validation. Tests cover malformed JSON, missing fields, null review, rejected findings, damaged cast indexes, photo metadata, and a rejected upper record alongside a valid lower. |
| P2 | Companion fetch failures were silently swallowed. No visible retry existed, and `loaded` was set before rendering, making a malformed response's failure sticky until a reload. | Show a week-scoped notice and retry control; set `loaded` only after successful rendering and clear partial panels on failure. Browser regressions cover HTTP failure and render failure followed by successful retry, with dental history still available. Partial server validation failures display a notice alongside valid records. |
| P2 | Recursive benchmark discovery skipped paths named `private`, but followed a public-looking symlink to a private manifest. Its content could enter exported benchmark reports. | Reject symlinks at the discovered file and within the selected root. A regression links a private manifest into a public-looking directory and verifies no discovery. Explicit selection of a normal file remains supported. |
| P2 | Each impression photo was read and hashed twice per companion response: once against the index, then again against summary metadata. The current two photos caused roughly 42.5 MB of reads instead of 21.2 MB, plus full-file allocations. | Compare the two expected hashes first and stream one file hash using `hashlib.file_digest`. No cache weakens consent revocation or content checking. Regression coverage includes mismatched summary/index hashes, revoked consent, and changed bytes. |

The failing CLI, benchmark and recovery regressions were run before their fixes.
Original STLs, photographs, consent inventory, acquisition dates, subjective scores,
dental bite coordinates, and inferred-motion data are unchanged. No provider
behavior changed. Changes use the existing lightweight PR checks; expensive CI
suites remain manual.

## Ship assessment

**8/10 for this research-toolkit update after the fixes and recorded validation.**
This rating covers software behavior, not scan fidelity or clinical suitability.

Top remaining risks:

- Hash validation and later path-based serving are separate reads. A concurrent
  local file replacement could race a download. The current model assumes a trusted
  local dataset directory; fully defending hostile concurrent writers needs a
  single validated byte stream or immutable artifact storage.
- Companion summaries are generated JSON, not a complete versioned runtime schema.
  The new error isolation covers the demonstrated failures, but exotic malformed
  nested values may still fail rendering; the viewer now exposes a retryable error.
- Longitudinal readiness metrics count discovered manifests, not unique people or
  independent acquisitions. Multiple visit/companion manifests can affect the
  denominator. A subject/visit grouping policy is needed before interpreting these
  metrics as cohort-level readiness; this audit does not silently choose one.
- Geometry scale, impression accuracy, physical damage and repeat independence
  remain unverified where marked. Mesh integrity and photos do not settle these.

## Three highest-leverage follow-ups

1. Define a versioned companion-response schema and validate every record before
   publication and API rendering, with typed per-record rejection reasons.
2. Serve validated immutable artifact bytes, and measure cold/warm request latency
   before adding any hash cache. Preserve immediate per-asset consent checks.
3. Define unique-subject, visit and physical-object grouping for benchmark readiness;
   test repeated captures and companion manifests so file counts cannot imply
   independent longitudinal evidence.

Validation results and exact released commits are recorded in the release PR and
local release audit. No broad refactor or new acquisition claims were introduced.
