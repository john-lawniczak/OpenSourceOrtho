import { FDI_QUADRANTS, FDI_TEETH, highlightTextColor, parseToothSelection,
  toggleToothSelection, toothName } from "./tooth_selection.js";

const root = document.getElementById("toothExplorer");
const host = document.getElementById("toothExplorerViewer");
const input = document.getElementById("toothExplorerInput");
const color = document.getElementById("toothExplorerColor");
const error = document.getElementById("toothExplorerError");
const summary = document.getElementById("toothExplorerSummary");
const list = document.getElementById("toothExplorerList");
const grid = document.getElementById("toothExplorerGrid");
let selected = [];
let viewer = null;
let loading = false;
let unavailable = false;
const frames = [{ poses: FDI_TEETH.map((tooth) => ({ tooth })) }];

for (const quadrant of FDI_QUADRANTS) {
  const group = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = quadrant.name;
  group.append(legend);
  for (const tooth of quadrant.teeth) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.fdi = String(tooth);
    button.textContent = String(tooth);
    button.setAttribute("aria-label", `FDI ${tooth}: ${toothName(tooth)}`);
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => select(toggleToothSelection(selected, tooth)));
    group.append(button);
  }
  grid.append(group);
}

function draw() {
  root.style.setProperty("--tooth-highlight", color.value);
  root.style.setProperty("--tooth-highlight-text", highlightTextColor(color.value));
  for (const button of grid.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(selected.includes(button.dataset.fdi)));
  }
  summary.textContent = selected.length
    ? `${selected.length} ${selected.length === 1 ? "tooth" : "teeth"} selected: ${selected.join(", ")}.`
    : "No teeth selected. Enter FDI numbers or select the numbered buttons.";
  list.replaceChildren(...selected.map((tooth) => {
    const item = document.createElement("li");
    item.textContent = `${tooth} · ${toothName(tooth)}`;
    return item;
  }));
  for (const swatch of root.querySelectorAll("[data-highlight-color]")) {
    swatch.setAttribute("aria-pressed", String(swatch.dataset.highlightColor === color.value));
  }
  viewer?.update({ frames, stageIndex: 0, view: "planned", exaggeration: 1,
    showToothLabels: true, labelTeeth: selected, highlightTeeth: selected, highlightColor: color.value });
}

function select(teeth) {
  selected = teeth;
  input.value = teeth.join(" ");
  input.removeAttribute("aria-invalid");
  error.textContent = "";
  draw();
}

document.getElementById("toothExplorerForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const result = parseToothSelection(input.value);
  if (result.invalid.length) {
    error.textContent = `Unknown FDI numbers: ${result.invalid.join(", ")}. Use 11–18, 21–28, 31–38, or 41–48. Selection unchanged.`;
    input.setAttribute("aria-invalid", "true");
    return;
  }
  select(result.teeth);
});
document.getElementById("toothExplorerClear").addEventListener("click", () => select([]));
document.getElementById("toothExplorerExample").addEventListener("click", () => select(["11", "12", "33", "34", "43", "44"]));
color.addEventListener("input", draw);
for (const swatch of root.querySelectorAll("[data-highlight-color]")) {
  swatch.addEventListener("click", () => { color.value = swatch.dataset.highlightColor; draw(); });
}
document.getElementById("toothExplorerResetView").addEventListener("click", () => viewer?.recenter());

// Keep this independent of treatment state and patient mesh caches. Only mount
// WebGL while the Tooth Map is visible, releasing its resources on navigation.
async function syncViewer() {
  if (!host.clientWidth || !host.clientHeight) {
    viewer?.dispose();
    viewer = null;
    return;
  }
  if (viewer) { viewer.resize(); viewer.recenter(); return; }
  if (loading || unavailable) return;
  loading = true;
  try {
    const { createViewer } = await import("./viewer3d.js");
    if (!host.clientWidth || !host.clientHeight) return;
    viewer = createViewer(host, { schematicOnly: true });
    viewer.setSelectionEnabled(true);
    viewer.setSelectionHandler((tooth) => select(toggleToothSelection(selected, tooth)));
    draw();
  } catch {
    unavailable = true;
    host.textContent = "3D is unavailable in this browser. Use the numbered tooth buttons and selected-tooth list below.";
  } finally {
    loading = false;
  }
}
new ResizeObserver(syncViewer).observe(host);
new MutationObserver(draw).observe(document.body, { attributes: true, attributeFilter: ["data-theme"] });
draw();
