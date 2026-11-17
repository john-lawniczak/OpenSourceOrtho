import { trimSurface } from "./surface_trim.js";

export function setupSurfaceTrim(getState, applyEdit, isBusy) {
  const el = id => document.getElementById(id);
  let selected = new Set();
  function update() {
    el("trimApply").disabled = !selected.size || isBusy();
    el("trimClear").disabled = !selected.size || isBusy();
    const labels = getState().edits?.labels || [];
    const painted = [...selected].filter(f => labels[f]).length;
    el("trimStatus").textContent = `${selected.size.toLocaleString()} faces selected in red${painted ? ` (${painted.toLocaleString()} painted)` : ""}. Apply removes everything marked red completely. Undo surface edit restores it. Open edges may remain.`;
    getState().viewer?.showTrim(selected);
  }
  el("trimClear").onclick = () => { selected = new Set(); update(); };
  el("trimApply").onclick = () => {
    if (!selected.size || isBusy()) return;
    const faces = new Set(selected);
    // Apply is explicit approval for this red selection, including painted faces.
    applyEdit((scan, labels) => trimSurface(scan, labels, faces, true),
      "Everything marked red was removed in a separate copy. Undo surface edit restores it. Save locally to keep this version.");
  };
  return {
    update,
    reset() { selected = new Set(); update(); },
    paint(faces, mode) {
      if (!["trim", "untrim"].includes(mode)) return false;
      if (isBusy()) return true;
      for (const f of faces) {
        if (mode === "untrim") selected.delete(f);
        else selected.add(f);
      }
      update(); return true;
    },
  };
}
