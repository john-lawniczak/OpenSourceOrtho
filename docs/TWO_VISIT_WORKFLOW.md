# Two-visit research workspace

Open **Fit another scan pair** in sample scan history, or `/progress.html`.
Choose baseline and later STL files for one arch, identify their dates and
orientation, and explicitly confirm a shared coordinate scale. Fitting runs
locally in a bounded, cancellable geometry worker; it does not call a model API.
No scale is fitted automatically. Units are user declarations, not independently
verified measurements. Week slots 1–7 describe the comparison, not elapsed dates.

Review the fitted regions individually, export either endpoint's draft labels,
and load that STL and label file in **Correct tooth boundaries and numbers**.
Brush/split/merge or renumber regions, save corrections, then import them for the
matching visit and regenerate. Corrected target FDI labels replace projected
matches; absent corrected target IDs are held. Review flags on boundaries never
promote the resulting motion to reviewed anatomy or treatment data.

Optional reference tooth numbers require corrected labels on both visits and
limit whole-arch registration to those labeled faces. Their anatomical stability
is not assumed. Without references, whole-arch best fit may remove global motion.

**Save locally** stores the two original scan buffers, fitted result, units,
orientation, dates, and corrections in this browser's IndexedDB. Opening a saved
case restores its viewer and permits refitting even after temporary jobs expire.
The storage is specific to this browser and local server origin; it is not an
account backup or a portable case export. Inputs changing invalidate old results.
Uploaded files also remain in the ignored local mesh workspace.

The endpoint artifact stores compact source and target ownership masks, allowing
independent benchmark identities to be scored without repeating huge face lists.
The optional motion-preview dependency extra is required by the local worker.
