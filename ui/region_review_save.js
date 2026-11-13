import { autoGrowTextarea } from "./auto_textarea.js";
const el = id => document.getElementById(id);

export async function fetchBaselineSave(arch, visit = "initial") {
  const response = await fetch(`/api/region-corrections/${arch}?visit=${encodeURIComponent(visit)}`, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error((result.errors || ["Could not read saved labels."]).join(" "));
  return result;
}

// Disk snapshots are explicit, immutable saves. Editing never silently marks a
// whole scan reviewed or replaces the published motion-preview labels.
export function setupRegionSaving(getContext) {
  const resizeNotes = autoGrowTextarea(el("reviewNotes"));
  let dirty = false, revision = 0, baseSavedAt = null;
  function markDirty() { dirty = true; revision++; el("reviewSaveStatus").textContent = "Unsaved changes"; }
  function setSaved(record) {
    dirty = false; baseSavedAt = record?.saved_at || null;
    el("reviewNotes").value = record?.notes || ""; resizeNotes();
    el("reviewChecked").checked = record?.corrections?.reviewed === true;
    el("reviewSaveStatus").textContent = record?.saved
      ? record.corrections?.provenance === "automatic-draft" ? "Restored automatic draft · review tooth colors and boundaries" : `Restored ${record.review_status}`
      : "";
    el("reviewSavePath").textContent = record?.path || "";
  }
  function update() {
    const { scan } = getContext();
    el("reviewSaveLocal").disabled = !scan?.visit;
    el("reviewReload").disabled = !scan?.visit;
    el("reviewSaveLocal").title = scan?.visit ? "Save a versioned file on this computer" : "Local dataset saves are for USER_ONE weeks 1 and 7. Use Download corrections JSON for other scans.";
  }
  async function refreshSummary() {
    const visit = el("reviewVisit").value;
    for (const arch of ["upper", "lower"]) {
      try {
        const result = await fetchBaselineSave(arch, visit);
        if (el("reviewVisit").value !== visit) return;
        const badge = el(`reviewSaved${arch}`);
        badge.hidden = !result.saved;
        badge.textContent = `${arch} · ${result.review_status}`;
        badge.title = result.saved ? new Date(result.saved_at).toLocaleString() : "";
      } catch { el(`reviewSaved${arch}`).hidden = true; }
    }
  }
  el("reviewSaveLocal").onclick = async () => {
    const { scan, edits } = getContext();
    if (!scan?.visit) return;
    const version = revision;
    const corrections = edits.export(scan.sha256, el("reviewChecked").checked);
    const notes = el("reviewNotes").value;
    el("reviewSaveLocal").disabled = true;
    el("reviewSaveStatus").textContent = "Saving a local snapshot…";
    try {
      const response = await fetch("/api/region-corrections", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arch: scan.arch, visit: scan.visit, corrections, notes, base_saved_at: baseSavedAt }) });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error((result.errors || ["Save failed."]).join(" "));
      if (getContext().scan === scan) {
        baseSavedAt = result.saved_at;
        if (version === revision) dirty = false;
        el("reviewSavePath").textContent = result.path;
        el("reviewSaveStatus").textContent = `Saved ${scan.arch} ${result.review_status} locally${version !== revision ? " · newer edits unsaved" : ""}`;
      }
      await refreshSummary();
    } catch (error) { el("reviewSaveStatus").textContent = `Not saved: ${error.message}`; }
    finally { update(); }
  };
  el("reviewNotes").addEventListener("input", markDirty);
  el("reviewChecked").addEventListener("change", markDirty);
  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  return { update, markDirty, setSaved, refreshSummary,
    canReplace: () => !dirty || window.confirm("There are unsaved labels or notes. Cancel to save first, or OK to discard them and load another scan."),
    exported: () => { if (!getContext().scan?.visit && !el("reviewNotes").value) dirty = false; },
  };
}
