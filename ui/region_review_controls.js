import { toothName, FDI_QUADRANTS, universalToothNumber } from "./tooth_selection.js";

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
      el("reviewArchNotice").textContent = lower
        ? "Lower · FDI numbering"
        : "Upper · FDI numbering";
      for (const quadrant of FDI_QUADRANTS.filter(q => q.name.startsWith(lower ? "Lower" : "Upper"))) {
        const group = document.createElement("div"); group.className = "review-tooth-quadrant";
        const heading = document.createElement("p");
        heading.textContent = `Your ${quadrant.name.toLowerCase()}`;
        const row = document.createElement("div"); row.className = "review-tooth-row";
        for (const number of quadrant.teeth) {
          const id = String(number), button = document.createElement("button"); button.type = "button";
          button.textContent = id; button.dataset.tooth = id;
          const us = document.createElement("small"); us.textContent = `US ${universalToothNumber(id)}`; button.append(us);
          button.title = toothName(id); button.setAttribute("aria-label", `FDI ${id} · US ${universalToothNumber(id)} · ${toothName(id)}`);
          button.onclick = () => { el("reviewTo").value = id; selectTooth(); };
          row.append(button);
        }
        group.append(heading, row); el("reviewTeeth").append(group);
      }
    },
    update(loaded, count = 0) {
      el("reviewEditing").disabled = !loaded; el("reviewExport").disabled = !loaded;
      const id = el("reviewTo").value, mode = el("reviewTool").value;
      for (const button of el("reviewTeeth").querySelectorAll("button")) button.setAttribute("aria-pressed", String(button.dataset.tooth === id));
      for (const button of document.querySelectorAll("[data-review-mode]")) button.setAttribute("aria-pressed", String(button.dataset.reviewMode === mode));
      el("regionCanvas").dataset.mode = mode;
      el("reviewSelectedTooth").textContent = loaded ? `FDI ${id} / US ${universalToothNumber(id)} · ${toothName(id)}` : "Choose a scan first";
      el("reviewFocus").disabled = !loaded || !count;
      el("reviewZoomIn").disabled = !loaded; el("reviewZoomOut").disabled = !loaded;
      el("reviewSelectionHelp").textContent = !loaded ? "" : count
        ? `${count.toLocaleString()} labeled faces · identity unconfirmed`
        : `No surface is labeled ${id} yet. Choose its crown, then paint.`;
      const messages = {
        orbit: "Drag to rotate · Right-drag to pan · Double-click a labeled crown to focus",
        brush: `Paint tooth ${id} · [ smaller · ] larger`,
        erase: "Erase to context · [ smaller · ] larger",
        split: `Split ${el("reviewFrom").value} → ${id}`,
      };
      el("reviewModeHelp").textContent = loaded ? messages[mode] : "Choose Upper or Lower to begin.";
    },
  };
}
