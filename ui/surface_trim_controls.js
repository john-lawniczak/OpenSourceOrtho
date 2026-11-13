import { trimSurface } from "./surface_trim.js";

export function setupSurfaceTrim(getState, applyEdit, isBusy) {
  const el = id => document.getElementById(id);
  let selected = new Set();
  function update() {
    el("trimApply").disabled = !selected.size || isBusy();
    el("trimClear").disabled = !selected.size || isBusy();
    el("trimAllowPainted").disabled = isBusy();
    el("trimStatus").textContent = `${selected.size.toLocaleString()} faces selected in red. Apply removes only this selection; it may leave open edges.`;
    getState().viewer?.showTrim(selected);
  }
  el("trimClear").onclick = () => { selected = new Set(); update(); };
  el("trimAllowPainted").onchange = () => {
    if (!el("trimAllowPainted").checked) selected = new Set([...selected].filter(f => !getState().edits.labels[f]));
    update();
  };
  el("trimApply").onclick = () => {
    if (!selected.size || isBusy()) return;
    const faces = new Set(selected), allowPainted = el("trimAllowPainted").checked;
    applyEdit((scan, labels) => trimSurface(scan, labels, faces, allowPainted),
      "Selected model surface removed in a separate copy. Undo surface edit restores it. Save locally to keep this version.",
      labels => { if (!allowPainted && [...faces].some(f => labels[f])) throw new Error("Selection now includes painted teeth. Clear it or allow removing painted surfaces."); });
  };
  return {
    update,
    reset() { selected = new Set(); el("trimAllowPainted").checked = false; update(); },
    paint(faces, mode) {
      if (!["trim", "untrim"].includes(mode)) return false;
      if (isBusy()) return true;
      const labels = getState().edits.labels;
      for (const f of faces) {
        if (mode === "untrim") selected.delete(f);
        else if (!labels[f] || el("trimAllowPainted").checked) selected.add(f);
      }
      update(); return true;
    },
  };
}
