import { suggestedPaintingCapture } from "./scan_week_eighteen.js";
import { autoGrowTextarea } from "./auto_textarea.js";
import { saveBrowserPainting } from "./region_browser_saves.js";
const el = id => document.getElementById(id);

export async function fetchBaselineSave(arch, visit = "initial", capture = "original") {
  const response = await fetch(`/api/region-corrections/${arch}?visit=${encodeURIComponent(visit)}${capture === "original" ? "" : `&capture=${encodeURIComponent(capture)}`}`, { cache: "no-store" });
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error((result.errors || ["Could not read saved labels."]).join(" "));
  return result;
}

// Dataset snapshots are immutable files; personal drafts live in browser storage.
// Editing never silently marks a scan reviewed or replaces motion-preview labels.
export function setupRegionSaving(getContext) {
  const resizeNotes = autoGrowTextarea(el("reviewNotes"));
  let dirty = false, revision = 0, baseSavedAt = null;
  function markDirty() { dirty = true; revision++; el("reviewSaveStatus").textContent = "Unsaved changes"; }
  function setSaved(record) {
    revision++; dirty = false; baseSavedAt = record?.saved_at || null;
    el("reviewNotes").value = record?.notes || ""; resizeNotes();
    el("reviewChecked").checked = record?.corrections?.reviewed === true;
    el("reviewSaveStatus").textContent = record?.saved
      ? record.corrections?.provenance === "automatic-draft" ? "Restored automatic draft · review tooth colors and boundaries" : `Restored ${record.review_status}`
      : "";
    el("reviewSavePath").textContent = record?.path || "";
  }
  function update() {
    const { scan } = getContext();
    el("reviewSaveLocal").disabled = !scan;
    el("reviewReload").disabled = !scan?.visit;
    el("reviewSaveLocal").title = scan?.visit ? "Save a versioned file on this computer" : "Save painting and notes in this browser";
  }
  async function refreshSummary() {
    const visit = el("reviewVisit").value;
    const captureFor = arch => {
      const { scan } = getContext();
      return scan?.visit === visit && scan.arch === arch ? scan.capture || "original" : suggestedPaintingCapture(arch, visit);
    };
    const captures = { upper: captureFor("upper"), lower: captureFor("lower") };
    for (const arch of ["upper", "lower"]) {
      try {
        const result = await fetchBaselineSave(arch, visit, visit === "progress-02" ? captures[arch] : "original");
        if (el("reviewVisit").value !== visit || captureFor(arch) !== captures[arch]) return;
        const badge = el(`reviewSaved${arch}`);
        badge.hidden = !result.saved;
        badge.textContent = `${arch} · ${result.review_status}`;
        badge.title = result.saved ? new Date(result.saved_at).toLocaleString() : "";
      } catch { el(`reviewSaved${arch}`).hidden = true; }
    }
  }
  el("reviewSaveLocal").onclick = async () => {
    const { scan, edits } = getContext();
    if (!scan) return;
    const version = revision;
    const corrections = edits.export(scan.sha256, el("reviewChecked").checked);
    const notes = el("reviewNotes").value;
    el("reviewSaveLocal").disabled = true;
    el("reviewSaveStatus").textContent = "Saving a local snapshot…";
    try {
      let result;
      if (!scan.visit) result = await saveBrowserPainting(scan, corrections, notes, baseSavedAt);
      else {
        const response = await fetch("/api/region-corrections", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ arch: scan.arch, visit: scan.visit, capture: scan.capture || "original", corrections, notes, base_saved_at: baseSavedAt }) });
        result = await response.json();
        if (!response.ok || !result.ok) throw new Error((result.errors || ["Save failed."]).join(" "));
      }
      if (getContext().scan === scan) {
        baseSavedAt = result.saved_at;
        if (version === revision) dirty = false;
        el("reviewSavePath").textContent = result.path;
        el("reviewSaveStatus").textContent = `Saved ${scan.arch} ${result.review_status} locally${version !== revision ? " · newer edits unsaved" : ""}`;
      }
      if (scan.visit) await refreshSummary();
    } catch (error) { if (getContext().scan === scan) el("reviewSaveStatus").textContent = `Not saved: ${error.message}`; }
    finally { update(); }
  };
  el("reviewNotes").addEventListener("input", markDirty);
  el("reviewChecked").addEventListener("change", markDirty);
  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  return { update, markDirty, setSaved, refreshSummary, savedAt: () => baseSavedAt, revision: () => revision,
    requireUnchanged: version => { if (version !== revision) throw new Error("Import stopped because painting or notes changed while loading. Save your changes, then import again."); },
    canLeave: () => { if (dirty && !window.confirm("Leave without saving your latest painting or notes? Choose Cancel to save first.")) return false; dirty = false; return true; },
    canReplace: () => !dirty || window.confirm("There are unsaved labels or notes. Cancel to save first, or OK to discard them and load another scan."),
    exported: () => { if (!getContext().scan?.visit && !getContext().scan?.repair && !el("reviewNotes").value) dirty = false; },
  };
}
