const el = id => document.getElementById(id);

export async function fetchBaselineSave(arch) {
  const response = await fetch(`/api/region-corrections/${arch}`);
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error((result.errors || ["Could not read saved labels."]).join(" "));
  return result;
}

// Disk snapshots are explicit, immutable saves. Editing never silently marks a
// whole scan reviewed or replaces the published motion-preview labels.
export function setupRegionSaving(getContext) {
  let dirty = false, revision = 0;
  function markDirty() { dirty = true; revision++; el("reviewSaveStatus").textContent = "Unsaved changes · save before switching scans or leaving."; }
  function setSaved(record) {
    dirty = false;
    el("reviewNotes").value = record?.notes || "";
    el("reviewChecked").checked = record?.corrections?.reviewed === true;
    el("reviewSaveStatus").textContent = record?.saved
      ? `Restored ${record.review_status} · ${record.saved_at}. Local file: ${record.path}`
      : "No local snapshot loaded. Save locally to keep USER_ONE baseline labels between sessions.";
  }
  function update() {
    const { scan } = getContext();
    el("reviewSaveLocal").disabled = !scan?.baseline;
    el("reviewSaveLocal").title = scan?.baseline ? "Save a versioned file on this computer" : "Local dataset saves are for USER_ONE baselines. Use Download corrections JSON for other scans.";
  }
  async function refreshSummary() {
    for (const arch of ["upper", "lower"]) {
      try {
        const result = await fetchBaselineSave(arch);
        el(`reviewSaved${arch}`).textContent = result.saved ? `${arch}: ${result.review_status} saved ${new Date(result.saved_at).toLocaleString()}` : `${arch}: not saved locally yet`;
      } catch { el(`reviewSaved${arch}`).textContent = `${arch}: local save status unavailable`; }
    }
  }
  el("reviewSaveLocal").onclick = async () => {
    const { scan, edits } = getContext();
    if (!scan?.baseline) return;
    const version = revision;
    const corrections = edits.export(scan.sha256, el("reviewChecked").checked);
    const notes = el("reviewNotes").value;
    el("reviewSaveLocal").disabled = true;
    el("reviewSaveStatus").textContent = "Saving a local snapshot…";
    try {
      const response = await fetch("/api/region-corrections", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arch: scan.arch, corrections, notes }) });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error((result.errors || ["Save failed."]).join(" "));
      if (getContext().scan === scan) {
        if (version === revision) dirty = false;
        el("reviewSaveStatus").textContent = `Saved ${scan.arch} ${result.review_status} locally. ${version !== revision ? "Newer edits are still unsaved. " : ""}File: ${result.path}`;
      }
      await refreshSummary();
    } catch (error) { el("reviewSaveStatus").textContent = `Not saved: ${error.message}`; }
    finally { update(); }
  };
  el("reviewNotes").addEventListener("input", markDirty);
  el("reviewChecked").addEventListener("change", markDirty);
  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  void refreshSummary();
  return { update, markDirty, setSaved,
    canReplace: () => !dirty || window.confirm("There are unsaved labels or notes. Cancel to save first, or OK to discard them and load another scan."),
    exported: () => { if (!getContext().scan?.baseline && !el("reviewNotes").value) dirty = false; },
  };
}
