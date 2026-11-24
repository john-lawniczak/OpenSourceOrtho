# Donate your own dental scans

Patients can help OpenSource Ortho develop and evaluate a clear-aligner planning
safety playground and research toolkit by voluntarily donating existing records.
`USER_ONE` is the first tracked donor case. Before/after and progress scan pairs
are especially useful for longitudinal comparisons; one scan pair is welcome.
Missing weeks are fine: observed scans and estimated intermediate poses remain
separately labeled. A donation does not provide treatment advice or review.

## Privacy review and withdrawal

We will work with you to remove identifying information and review the exact
files before publication. This is a manual, best-effort de-identification process;
there is no automatic anonymization service, and dental anatomy or case details
can still identify you. Do not send identifiable originals until a private
review route and handling arrangements have been agreed.

You can withdraw an unpublished donation before release. After public release,
you can request that we stop including it in future distributions, but we cannot
guarantee removal from Git history, downloads, forks, or downstream models.
Valid open-license permissions on released copies cannot simply be revoked.
Submission through a public PR or issue is already public release; a private
inquiry or private review submission is not. These terms do not waive applicable
privacy rights. Review and approve the final file list before publication.

## Request copies of existing records

In the United States, HIPAA generally gives individuals access to their health
information in a HIPAA-covered entity's designated record set, including
diagnostic images. The requested electronic format must be provided when readily
producible. This is not an unconditional entitlement to every proprietary export
or a newly created record. See the [HHS access guidance](https://www.hhs.gov/hipaa/for-professionals/faq/right-to-access-and-research/index.html).
Outside the US, ask your provider about local records-access rules.

Send this request to your dental office through its own records-request process.
Supply identifying details only to the office, never in a project issue:

> Please provide electronic copies of my existing dental records, including
> upper/lower intraoral scans from baseline, progress, refinement, and final
> visits, plus bite scans if available. I would prefer STL, PLY, or OBJ exports
> where readily producible, with units and visit order. Please also include
> existing CBCT images in DICOM format and their reports, if held, and any
> available treatment summary or plan animation. If a requested format is not
> readily producible, please explain the available electronic alternatives.
> Please tell me about any applicable copying charges and how I can receive
> these records directly.

Request only records that already exist. Do not obtain new imaging for this
project. Receiving a copy does not establish permission to redistribute a
provider's or vendor's copyrighted material. Confirm rights separately for plan
videos, screenshots, proprietary exports, annotations, and other third-party
assets. Cropping a logo does not establish redistribution rights.

## Prepare and submit a donation

1. **Start with a records-free inquiry.** Open an issue in the public project
   saying which types of scans and approximate relative weeks you could donate.
   Do not attach records or disclose your identity, clinic, dates, or history.
   A public GitHub account can itself connect you to the eventual case; consider
   that before participating. If you need private review, ask for an agreed
   private transfer route before sending files. This project does not currently
   provide a dedicated secure patient-upload portal.
2. **Prepare copies locally.** Keep originals and identifying paperwork outside
   Git or in ignored `datasets/<specimen>/.local/`. Remove identifiers from
   filenames, file headers, metadata, images, and notes; use relative treatment
   weeks instead of dates. A UUID or renamed file alone does not de-identify a
   record. CBCT may contain facial anatomy, identifying tags, and burned-in text.
   Raw DICOM is excluded from the current public dataset path; discuss only
   reviewed, de-identified derived anatomy or redacted metadata for publication.
3. **Select exact files and rights.** Follow the
   [case-bundle standard](DATA_CONTRIBUTION.md), then complete the
   [consent form](DATA_DONATION_CONSENT.md). Choose CC0 1.0 or CC BY 4.0 only
   where you hold the necessary rights or have documented permission. Keep
   third-party assets with unresolved rights out of the bundle.
4. **Review before uploading.** Check the actual files for identifiers and agree
   with a maintainer on scope, consent, license, attribution, and transfer method.
   Registration is local and does not upload or anonymize your scans. Public
   forks, PRs, issue attachments, and Git history are already publication, even
   if a PR is never merged. Upload only the reviewed, explicitly authorized
   bundle through the agreed route or a public PR when ready to publish.
5. **Record publication scope.** Maintainers validate the manifest and enumerate
   every public file in `consent.json`, including the sanitized consent statement
   and `DATA_LICENSE.md`. Keep signed paperwork and identity/contact details
   private. Run `python3 tools/build_dataset_catalog.py --check` after updating
   the catalog. Maintainer releases follow [PRIVATE_DEVELOPMENT.md](PRIVATE_DEVELOPMENT.md).

## Choose the data license deliberately

| Choice | What reuse it permits |
|---|---|
| [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Waives copyright and related rights to the extent possible; permits copying, modification, and commercial reuse without attribution requirements. |
| [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Permits copying, modification, and commercial reuse with attribution, a license link, and an indication of changes. Use an agreed non-identifying attribution label. |

Both choices allow broad reuse, including research, benchmarking, and model
development. Neither clears third-party rights or guarantees anonymity. Public
geometry and longitudinal details may still identify someone. Copies, forks,
and trained models cannot reliably be recalled; stopping future project hosting
does not revoke valid licenses on copies already released.

For each new donation, add `DATA_LICENSE.md` listing asset paths, SHA-256 hashes,
the chosen license and its URL, and attribution text where applicable. Keep
this separate from `consent.json`: the existing JSON schema records publication
scope and does not accept arbitrary license fields. New files or changed files
require renewed scope review. This policy does not retroactively relicense
USER_ONE or any existing dataset.

## Inviting other patients

You may share this guide in aligner forums or subreddits where community rules
permit recruitment. Ask moderators first when required. Invite people to request
their own records and decide privately whether to donate; never collect records
in public replies or copy another person's posted scans. Participation is
voluntary, and no clinical benefit or guaranteed anonymity should be promised.
