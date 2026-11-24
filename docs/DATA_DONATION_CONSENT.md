# Patient data publication consent and license selection

Copy and complete this form for a new donation. It records a voluntary public
data contribution, not permission to obtain records from a provider or consent
to treatment. Read the [donation guide](PATIENT_DATA_DONATION.md) first.
Do not put names, signatures, contact details, birth dates, or medical record
numbers in the public copy. Any necessary identity verification or signed
paperwork must use an agreed private route and stay outside the repository.

## Scope to complete

- Specimen UUID: ____________________
- Non-identifying donor pseudonym: ____________________
- Public CC BY attribution text, if selected: ____________________
- Sanitized consent statement filename: ____________________
- Data-license inventory filename: `DATA_LICENSE.md`
- Publication scope: ____________________
- Exact dates: excluded by default; any requested exception and reason must be
  separately documented and reviewed: ____________________

List every proposed public asset, including metadata, notes, annotations, and
media. Add rows as needed; do not use directory wildcards. Record the hashes of
final data files in `DATA_LICENSE.md` before release.

| Case-relative asset path | Description / observed or derived | Rights basis | License: CC0 1.0 or CC BY 4.0 |
|---|---|---|---|
| ____________________ | ____________________ | ____________________ | ____________________ |

Rights basis means your authority to license the file or documented permission
from the relevant rights holder. Possession of your medical record alone is not
proof of copyright ownership. Exclude unresolved third-party material.

## Donor acknowledgements

Leave all boxes unchecked until you personally agree. Maintainers must not
complete these on a donor's behalf or infer consent from an upload alone.

- [ ] I am an adult donating my own records voluntarily. Records for minors or
      other people require a separately established consent process.
- [ ] I have reviewed the exact listed files and have authority to share and
      license them. Any necessary third-party permission is documented.
- [ ] I authorize OpenSource Ortho to publish these files and their reviewed
      derivatives for public access, research, benchmarking, software testing,
      and model development under the selected terms.
- [ ] I select the license recorded for each listed asset: either
      [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) or
      [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). I understand
      these terms permit commercial reuse and modified versions, and CC BY
      requires the specified attribution. I am not transferring ownership.
- [ ] I reviewed filenames, metadata, visible content, and notes for identifying
      information with the maintainer. I understand de-identification is a
      best-effort review, not an automatic service or guarantee of anonymity;
      dental anatomy and case details may still be linked to me.
- [ ] I understand a public contribution can be downloaded, copied, forked, and
      reused by others. I can withdraw a private, unpublished submission before
      publication or request removal
      from future project distributions, but existing copies cannot reliably
      be recalled and valid open-license permissions are not revoked.
- [ ] I understand that public PRs and issue attachments are already public,
      even before a maintainer accepts them. This form does not waive applicable
      privacy rights.
- [ ] I understand donation does not provide diagnosis, treatment planning,
      clinical approval, payment, or a promise of personal benefit. I do not
      need new scans or imaging to participate.
- [ ] My permission covers only the listed files. Later visits, additional files,
      and changes to publication scope require further review and authorization.

Donor affirmation, using only the pseudonym above: ____________________

## Maintainer review record

- [ ] A completed donor affirmation was received; provenance is documented
      without publishing identity or private correspondence.
- [ ] Actual files, publication scope, rights, selected licenses, attribution,
      and any date exception were reviewed.
- [ ] Raw DICOM, identifying paperwork, and unresolved third-party assets are
      excluded; observed scans and derived estimates are distinguished.
- [ ] `manifest.json`, `DATA_LICENSE.md`, and `consent.json` agree with the
      release bundle. Every public asset is individually allowlisted.

Record the non-identifying authorization basis in `consent.json`. That JSON
file is a publication-scope record, not a substitute for the donor's completed
statement. Do not treat this blank template as evidence of consent or apply
its license choices retroactively to existing contributions.
