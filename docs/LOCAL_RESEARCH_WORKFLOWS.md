# Saved labels, captures and recoverable edits

These local tools extend the exploratory workflow. Original scans, inferred
history and applied planning edits remain separate.

## Refit USER_ONE from saved painting

In **Scan history → Scan details & match quality → Saved-label experiments**,
choose upper or lower, then **Refit saved painting**. This uses the current week 1
and week 7 labels. When week 7 painting is unavailable, the fixed local hybrid
segmenter supplies a draft fallback; it does not block an exploratory preview.

Each result retains both original scan hashes, rotations, units, frozen label
snapshots and hashes, generator/configuration and pipeline-code fingerprints.
It records fitted/uncertain/unmatched counts, mean per-region p90 surface
residual with its denominator, the bundled-fit summary and previous-fit summary.
The bundled artifacts and earlier experiments are never overwritten. Choose
**Bundled fit** or a saved fit explicitly. Changed inputs mark earlier fits stale;
their reports remain available, but regenerating is required to display them as
current estimates. Original observations stay available.

The preview still labels intermediate weeks as estimates. Surface agreement,
including lower residuals or fewer weak matches, does not establish tooth-motion
accuracy. Whole-arch registration and unverified scale retain their limitations.

**Compare automatic labels** compares the bundled automatic *moving/target face
masks* with a frozen copy of current contributor painting on the same original
faces. These bundled masks include the existing crown cropping and endpoint
transfer, so they are not an independent segmentation reference. Reports include
FDI-specific IoU/precision/recall, per-reference label confusion counts, missing
identities, coverage counts and explicit denominators. Unpainted reference faces
are unknown, not established gum. Boundary distances, correction time, automatic
segmentation runtime and independent anatomical accuracy remain unavailable.

Fits, review events and reports live in ignored `.orthoplan-research/` directories
(or `ORTHOPLAN_RESEARCH_STORE`). Downloads contain contributor annotations and
remain private unless separately authorized. No hosted model is called.

## Durable contributor reviews

On **Explore individual teeth**, select a crown, check its number/boundary, and
optionally add your name, notes or uncertainty under **Review notes**. Saving is
required before the review enables a movement preview. “Uncertain” and “unchecked”
do not enable editing. This is a self-reported contributor review, not independent
clinical review.

A review binds the original source hash, FDI identity and exact region mask.
Changing that region or source invalidates it on reload; changing an unrelated
region does not. Review history is append-only. It does not promote fitted poses
or confer review on another tooth. Review persistence currently covers USER_ONE
painted scans; generalized uploaded-case reviews remain backlog work.

## Alternative captures at the same visit

**Compare two scans** accepts several STL files per endpoint. Use **Active
capture** to choose which one enters the fit. Alternatives stay within that
visit and arch; they do not create extra weeks. Each capture retains its original
bytes/hash, capture date, local import time, model/cast ID, damage notes,
orientation and corrected labels. The model ID is contributor-entered evidence,
not proof that two captures share a cast.

Save both selected visits before fitting if desired. Local saves and v2 portable
backups retain all alternatives and the active choices; v1 backups still open.
Switching captures invalidates the current fit and match overrides. Imports are
bounded to eight captures per endpoint, 100 MB per scan and 180 MB per case.
A general multi-visit graph, composite models and measured repeatability are
separate future work.

## Undo, redo and recovery

Applied tooth previews support **Undo** and **Redo**. Applying a new change after
undo clears the old redo branch. Pending proposals remain separate and cannot be
restored as applied edits.

Applied movements and hold choices save in the browser's IndexedDB. Reopen the
same scans and painting, then use **Recover applied edits → Restore edit session**.
The stored source/label binding and scan-unit settings must match. Restoring
replaces the working rows and hold choices and recovers up to 20 undo/redo steps;
it does not restore API keys, review flags or unpublished proposals. Browser
storage is local to the server address/profile. Existing plan-version exports
remain the portable path; named alternative editing branches are not added here.
