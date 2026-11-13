import { toothName, universalToothNumber } from "./tooth_selection.js";
import { focusedTeeth } from "./plan_focus.js";

// Stable arch rows surround the scan so labels do not overlap as the camera turns.
let host, signature = "";
const rows = [
  ["Upper", [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28]],
  ["Lower", [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38]],
];
export function renderViewerToothNumbers(teeth, selected, visible) {
  if (!host) {
    host = document.createElement("div"); host.className = "viewer-tooth-numbers";
    document.getElementById("viewer3d").append(host);
  }
  host.hidden = !visible || !teeth.length;
  const focus = focusedTeeth();
  const key = JSON.stringify([teeth, selected, focus]); if (key === signature) return;
  signature = key;
  const available = new Set(teeth);
  host.replaceChildren();
  for (const [arch, ids] of rows) {
    const row = document.createElement("div"); row.className = `viewer-tooth-row ${arch.toLowerCase()}`;
    row.setAttribute("role", "group"); row.setAttribute("aria-label", `${arch} tooth numbers`);
    const caption = document.createElement("span"); caption.textContent = `${arch} · FDI numbers`; row.append(caption);
    for (const id of ids.map(String)) {
      const button = document.createElement("button"); button.type = "button"; button.textContent = id;
      button.dataset.selectTooth = id; button.disabled = !available.has(id);
      button.classList.toggle("is-plan-focus", focus.includes(id));
      button.setAttribute("aria-pressed", String(selected === id));
      button.setAttribute("aria-label", `FDI ${id} · US ${universalToothNumber(id)} · ${toothName(id)}`);
      button.title = button.disabled ? `No identified region for FDI ${id}` : `FDI ${id} · US ${universalToothNumber(id)}`;
      row.append(button);
    }
    host.append(row);
  }
}
