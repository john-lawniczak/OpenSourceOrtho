import { toothName, FDI_QUADRANTS } from "./tooth_selection.js";

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
        ? "Editing LOWER arch · FDI 31–38 and 41–48. Upper numbers such as 18 do not apply here."
        : "Editing UPPER arch · FDI 11–18 and 21–28. For lower teeth, choose Lower above and load the lower scan.";
      for (const quadrant of FDI_QUADRANTS.filter(q => q.name.startsWith(lower ? "Lower" : "Upper"))) {
        const group = document.createElement("div"); group.className = "review-tooth-quadrant";
        const heading = document.createElement("p");
        heading.textContent = `Person’s ${quadrant.name.toLowerCase()} · ${quadrant.name.endsWith("right") ? "back → midline" : "midline → back"}`;
        const row = document.createElement("div"); row.className = "review-tooth-row";
        for (const number of quadrant.teeth) {
          const id = String(number), button = document.createElement("button"); button.type = "button";
          button.textContent = id; button.dataset.tooth = id;
          button.title = toothName(id); button.setAttribute("aria-label", `${id} · ${toothName(id)}`);
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
      el("reviewSelectedTooth").textContent = loaded ? `Selected ${id} · ${toothName(id)}` : "Choose a scan first";
      el("reviewFocus").disabled = !loaded || !count;
      const position = Number(id[1]);
      const location = `Position ${position} from the front midline on this side${position === 8 ? " (wisdom tooth; may be absent)" : ""}.`;
      el("reviewSelectionHelp").textContent = !loaded ? "" : count
        ? `${location} Amber marks the current label, not a confirmed tooth identity. Use Find selected label, then rotate to inspect it. In Move view, click a labeled surface to select its number.`
        : `${location} No surface is labeled ${id} yet, so there is nothing to highlight. Locate the crown using the guide, confirm its identity, then paint. A number alone cannot locate an unpainted or missing tooth.`;
      const messages = {
        orbit: "Move view: drag to rotate, scroll/pinch to zoom, right-drag to pan. Click a labeled surface or choose a number, then click Paint tooth.",
        brush: `Paint tooth ${id} · ${toothName(id)}: drag over its crown surface. Amber shows this label. Switch to Move view to rotate, then paint the other sides.`,
        erase: "Erase: drag over mislabeled faces to return them to gray context. This removes labels, not scan geometry.",
        split: `Split: drag to transfer faces from tooth ${el("reviewFrom").value} to ${id}. Other labels stay unchanged.`,
      };
      el("reviewModeHelp").textContent = loaded ? `Selected ${id} · ${toothName(id)}. ${messages[mode]}\n${count.toLocaleString()} faces labeled as tooth ${id}.` : "Load a scan to begin.";
    },
  };
}
