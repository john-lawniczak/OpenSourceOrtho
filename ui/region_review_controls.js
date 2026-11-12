import { toothName, FDI_QUADRANTS, universalToothNumber } from "./tooth_selection.js";

export function setupReviewControls({ selectTooth, changeMode }) {
  const el = id => document.getElementById(id);
  for (const button of document.querySelectorAll("[data-review-mode]")) {
    button.onclick = () => { el("reviewTool").value = button.dataset.reviewMode; changeMode(); };
  }
  el("reviewTool").onchange = changeMode;
  el("reviewTo").onchange = selectTooth;
  el("reviewSpillover").onclick = () => {
    el("reviewFrom").value = el("reviewTo").value;
    el("reviewSplitSource").value = el("reviewFrom").value;
    el("reviewTool").value = "split"; changeMode();
  };
  el("reviewSplitSource").onchange = () => { el("reviewFrom").value = el("reviewSplitSource").value; changeMode(); };
  el("reviewFrom").onchange = () => { el("reviewSplitSource").value = el("reviewFrom").value; changeMode(); };
  el("reviewSplitFlip").onclick = () => {
    if (el("reviewSplitFlip").disabled) return;
    const source = el("reviewFrom").value;
    el("reviewFrom").value = el("reviewTo").value;
    el("reviewSplitSource").value = el("reviewFrom").value;
    el("reviewTo").value = source;
    selectTooth(); changeMode();
  };
  return {
    arch(arch, absentTeeth = []) {
      const lower = arch === "lower";
      el("reviewArch").value = arch;
      el("reviewFrom").value = lower ? 31 : 11;
      el("reviewTo").value = lower ? 32 : 12;
      el("reviewTeeth").replaceChildren();
      el("reviewSplitSource").replaceChildren(new Option("0 · Unlabeled", "0"));
      el("reviewArchNotice").textContent = lower
        ? "Lower · FDI numbering"
        : "Upper · FDI numbering";
      if (absentTeeth.length) el("reviewArchNotice").textContent += " · wisdom teeth removed (reported)";
      for (const quadrant of FDI_QUADRANTS.filter(q => q.name.startsWith(lower ? "Lower" : "Upper"))) {
        const group = document.createElement("div"); group.className = "review-tooth-quadrant";
        const heading = document.createElement("p");
        heading.textContent = `Your ${quadrant.name.toLowerCase()}`;
        const row = document.createElement("div"); row.className = "review-tooth-row";
        for (const number of quadrant.teeth) {
          const id = String(number), button = document.createElement("button"); button.type = "button";
          button.textContent = id; button.dataset.tooth = id;
          const us = document.createElement("small"); us.textContent = `US ${universalToothNumber(id)}`; button.append(us);
          const kind = document.createElement("small");
          kind.textContent = ["", "Central", "Lateral", "Canine", "Premolar 1", "Premolar 2", "Molar 1", "Molar 2", "Wisdom"][number % 10];
          button.append(kind);
          button.dataset.kind = number % 10 <= 3 ? "front" : number % 10 <= 5 ? "premolar" : "molar";
          el("reviewSplitSource").append(new Option(`${id} · ${toothName(id)}`, id));
          button.title = toothName(id); button.setAttribute("aria-label", `FDI ${id} · US ${universalToothNumber(id)} · ${toothName(id)}`);
          if (absentTeeth.includes(number)) {
            button.disabled = true; kind.textContent = "Removed";
            button.title += " · removed, per contributor";
          }
          button.onclick = () => { el("reviewTo").value = id; selectTooth(); };
          row.append(button);
        }
        group.append(heading, row); el("reviewTeeth").append(group);
      }
    },
    update(loaded, count = 0) {
      el("reviewEditing").disabled = !loaded; el("reviewExport").disabled = !loaded;
      const id = el("reviewTo").value, mode = el("reviewTool").value;
      const source = el("reviewFrom").value;
      el("reviewSplitPanel").hidden = mode !== "split";
      el("reviewSplitSource").value = source;
      const presentTeeth = [...el("reviewTeeth").querySelectorAll("button")]
        .filter(button => !button.disabled).map(button => button.dataset.tooth);
      el("reviewSplitFlip").disabled = !loaded || mode !== "split" || source === id
        || !presentTeeth.includes(source) || !presentTeeth.includes(id);
      el("reviewSplitFlip").title = el("reviewSplitFlip").disabled
        ? "Choose two different, present tooth labels to flip."
        : `Swap to ${id} → ${source}; labels change only when you paint.`;
      el("reviewSplitHint").textContent = source === id
        ? "Now choose the correct destination tooth above."
        : `Paint ${source} → ${id}. All other labels stay protected.`;
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
        orbit: "Drag to rotate · Pan to move · Double-click any surface to focus",
        pan: "Drag to move the mouth · Scroll to zoom · Double-click any surface to focus",
        brush: `Paint tooth ${id} · [ smaller · ] larger`,
        erase: "Erase to context · [ smaller · ] larger",
        split: source === id ? "Choose the destination tooth, then paint the spillover." : `Paint only misplaced ${source} surfaces → ${id} · Undo restores the stroke`,
      };
      el("reviewModeHelp").textContent = loaded ? messages[mode] : "Choose Upper or Lower to begin.";
    },
  };
}
