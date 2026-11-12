import { toothName, FDI_TEETH } from "./tooth_selection.js";

export function setupReviewControls({ selectTooth, changeMode }) {
  const el = id => document.getElementById(id);
  for (const button of document.querySelectorAll("[data-review-mode]")) {
    button.onclick = () => { el("reviewTool").value = button.dataset.reviewMode; changeMode(); };
  }
  el("reviewTool").onchange = changeMode;
  el("reviewTo").onchange = selectTooth;
  return {
    arch(arch) {
      const lower = arch === "lower";
      el("reviewArch").value = arch;
      el("reviewFrom").value = lower ? 31 : 11;
      el("reviewTo").value = lower ? 32 : 12;
      el("reviewTeeth").replaceChildren();
      for (const id of FDI_TEETH.filter(id => lower ? /^[34]/.test(id) : /^[12]/.test(id))) {
        const button = document.createElement("button"); button.type = "button";
        button.textContent = id; button.dataset.tooth = id;
        button.title = toothName(id); button.setAttribute("aria-label", `${id} · ${toothName(id)}`);
        button.onclick = () => { el("reviewTo").value = id; selectTooth(); };
        el("reviewTeeth").append(button);
      }
    },
    update(loaded, count = 0) {
      el("reviewEditing").disabled = !loaded; el("reviewExport").disabled = !loaded;
      const id = el("reviewTo").value, mode = el("reviewTool").value;
      for (const button of el("reviewTeeth").children) button.setAttribute("aria-pressed", String(button.dataset.tooth === id));
      for (const button of document.querySelectorAll("[data-review-mode]")) button.setAttribute("aria-pressed", String(button.dataset.reviewMode === mode));
      el("regionCanvas").dataset.mode = mode;
      const messages = {
        orbit: "Move view: drag to rotate, scroll/pinch to zoom, right-drag to pan. Choose a tooth, then click Paint tooth.",
        brush: `Paint tooth ${id} · ${toothName(id)}: drag over its crown surface. Amber shows this label. Switch to Move view to rotate, then paint the other sides.`,
        erase: "Erase: drag over mislabeled faces to return them to gray context. This removes labels, not scan geometry.",
        split: `Split: drag to transfer faces from tooth ${el("reviewFrom").value} to ${id}. Other labels stay unchanged.`,
      };
      el("reviewModeHelp").textContent = loaded ? `${messages[mode]}\n${count.toLocaleString()} faces labeled as tooth ${id}.` : "Load a scan to begin.";
    },
  };
}
