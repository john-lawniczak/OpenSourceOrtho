// Only applied rows and hold choices are recoverable; proposals and credentials are excluded.
import { el, state } from "./state.js";
import { caseStore } from "./progress_case_store.js";
const clone = rows => rows.map(row => ({...row}));
export function pushEditUndo() {
  state.manualEdit.undoStack = [...(state.manualEdit.undoStack || []), clone(state.rows)].slice(-20);
  state.manualEdit.redoStack = [];
}
export function travelEdit(direction) {
  const from = direction === "undo" ? "undoStack" : "redoStack", to = direction === "undo" ? "redoStack" : "undoStack";
  if (state.goalPreview || state.goalBusy) return false;
  const rows = state.manualEdit[from]?.pop(); if (!rows) return false;
  state.manualEdit[to] = [...(state.manualEdit[to] || []), clone(state.rows)].slice(-20);
  state.rows = rows; return true;
}
function binding() {
  const annotations = state.segmentation.annotations;
  if (state.sample.active && annotations?.length) return JSON.stringify({sample:true, visit:state.sample.visit,
    sources:annotations.map(a=>[a.arch,a.source_sha256,a.labels_sha256])});
  const assets = state.segmentation.applied?.mesh_assets;
  return assets?.length ? JSON.stringify({sample:false, assets}) : null;
}
let saving = Promise.resolve();
export async function saveEditSession() {
  const key = binding(); if (!key) return;
  const record = {name:`plan-session:${key}`, schema:1, binding:key, saved_at:new Date().toISOString(),
    rows:clone(state.rows), held:[...state.guided.excludedTeeth], units:state.scanUnits,
    undo:(state.manualEdit.undoStack || []).map(clone), redo:(state.manualEdit.redoStack || []).map(clone)};
  const request = saving.catch(()=>{}).then(()=>caseStore("put",record,"edits")); saving = request;
  try { await request; el("editSessionStatus").textContent = "Applied edits saved in this browser."; }
  catch { el("editSessionStatus").textContent = "Edits could not be saved in this browser. Keep this tab open or save a plan version."; }
}
export function renderEditSession() {
  el("guidedEditRedo").disabled = !state.manualEdit.redoStack?.length || Boolean(state.goalPreview) || state.goalBusy;
  el("saveEditSession").disabled = !binding() || Boolean(state.goalPreview) || state.goalBusy;
  el("restoreEditSession").disabled = el("saveEditSession").disabled;
}
export function installEditSession(renderAll) {
  el("guidedEditRedo").onclick = () => { if (travelEdit("redo")) { renderAll(); void saveEditSession(); } };
  el("saveEditSession").onclick = saveEditSession;
  el("restoreEditSession").onclick = async () => {
    const key = binding(); if (!key || state.goalPreview || state.goalBusy) return;
    const baseline = JSON.stringify([state.rows,state.guided.excludedTeeth]);
    try {
      await saving.catch(()=>{});
      const record = await caseStore("get",`plan-session:${key}`,"edits");
      if (binding() !== key || baseline !== JSON.stringify([state.rows,state.guided.excludedTeeth]) || state.goalPreview || state.goalBusy) throw new Error("The workspace changed. Try restoring again.");
      if (!record || record.schema !== 1 || record.binding !== key) throw new Error("No saved session matches this scan and painting version.");
      if (JSON.stringify(record.units) !== JSON.stringify(state.scanUnits)) throw new Error("Restore the same scan-unit settings before recovering these edits.");
      const restored = validateEditSession(record, state.segmentation.applied.tooth_meshes.map(link=>String(link.tooth.value)));
      if (!window.confirm("Restore saved applied edits and hold choices? This replaces the current working edits.")) return;
      state.rows = restored.rows; state.guided.excludedTeeth = restored.held;
      state.manualEdit.undoStack = restored.undo; state.manualEdit.redoStack = restored.redo;
      renderAll(); el("editSessionStatus").textContent = `Restored applied edits saved ${record.saved_at.slice(0,19)}.`;
    } catch(error) { el("editSessionStatus").textContent = error.message; }
  };
}

export function validateEditSession(record, teeth) {
  const allowed = new Set(teeth);
  const rows = value => {
    if (!Array.isArray(value) || value.length > 20000 || value.some(r=>!r || !allowed.has(String(r.tooth))
      || !Number.isInteger(r.stage) || r.stage < 0 || !["x","y","z","tip","torque","rotation"].every(key=>Number.isFinite(r[key])))) throw new Error("Saved edit rows are invalid.");
    return clone(value);
  };
  const stack = value => {
    if (!Array.isArray(value) || value.length>20) throw new Error("Saved edit history is invalid.");
    return value.map(rows);
  };
  if (!Array.isArray(record.held) || record.held.some(t=>!allowed.has(t))) throw new Error("Saved hold choices do not match these teeth.");
  return {rows:rows(record.rows), held:[...record.held], undo:stack(record.undo), redo:stack(record.redo)};
}
