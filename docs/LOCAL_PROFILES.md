# Local profiles and saved progress

Use the dropdown arrow beside **Your Teeth Profile** to switch local workspaces.
The main button still opens your own teeth. Gear **Settings → Profiles** contains
the full selector, **Add profile**, **Rename**, and **Save progress**, keeping the
top bar clear. **Add profile** creates an empty workspace and switches to it;
**Rename** changes its display name without moving data. Existing
uploads, paintings and saved records remain under **My profile**. Names are local
display labels, not patient identifiers published to a dataset.

The main workspace saves automatically after a short pause. **Save progress**
saves immediately. Switching first saves the current workspace, then reloads the
selected profile. A failed save prevents switching. Pending movement previews
must be applied or discarded first. Save painting/cleanup changes with **Save
locally** in the precision editor, and two-visit cases in their own workspace.
Those records are separated by profile too.

## What resumes

- Original uploaded files and scan-date metadata, source references and units.
- Plan title/ID, working movement rows, hold choices and undo/redo history.
- Segmentation inputs and explicitly applied segmentation, imported record
  references, registrations and derived anatomy.
- Workflow position, settings and discussion notes. Paintings and saved
  two-visit cases remain accessible through their existing editors.

The bundled sample remains a separate example: opening it does not replace the
personal workspace saved for that profile. Applied sample editing sessions still
use their existing explicit save/recover workflow. Pending generation results,
temporary previews, API keys and provider permissions are not stored in profile
snapshots. Chat retains its existing tab-session lifetime, separately per profile.

## Storage and limits

IndexedDB already stores scan files and paintings, so this change extends that
browser database instead of introducing SQLite. Profile names and workspace
snapshots use `orthoplan-profiles`; uploads and editor databases retain their
original names for **My profile** and use a profile suffix for new profiles.
LocalStorage notes/review keys and tab chat keys are similarly separated.

The Python server uses the explicit `X-Ortho-Profile` identifier to separate plan
versions, saved sample painting notes and local research records. Worker requests
carry the same identifier. Default paths remain compatible with existing local
data and CLI commands; other plan versions live under `.orthoplan-profiles/`,
and correction/research roots contain `profiles/<id>/`. Original dataset assets
and content-addressed mesh storage remain shared.

These profiles are **not accounts or an access-control boundary**. Anyone using
the same browser can switch profiles. They do not synchronize across computers,
browsers or server addresses. Clearing browser storage can remove profiles and
browser-held scans; ordinary plan and repair-bundle exports remain useful backups.
A complete portable profile backup/restore is not implemented yet. SQLite would
be appropriate for a later server-managed store or desktop package with a unified
backup path, but is not necessary for a few browser-local workspaces.

Each open tab stays bound to its selected profile. Workspace saves compare
revision tokens in a single transaction, so a stale tab cannot overwrite newer
saved progress. Errors leave the working tab open. This does not add account
security or general collaborative editing.

## Verification

Browser checks cover three-profile switching, original file bytes, notes and
movement restoration, reload, autosave, legacy upload preservation, sample
isolation, rename/duplicate names, separate tabs, stale revisions and failed
storage. Server checks cover identical plan IDs in different profiles, painting
notes, research directories, worker context and invalid path identifiers.
Desktop/mobile layouts and the existing painting save/reopen flow are checked.
