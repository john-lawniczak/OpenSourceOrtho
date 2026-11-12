export function mountScanViewToolbar(before, onView, { compact = false, defaultView = false } = {}) {
  const bar = document.createElement("div");
  bar.className = "scan-view-controls"; bar.setAttribute("aria-label", "Scan view controls");
  const label = document.createElement("span"); label.textContent = "View"; bar.append(label);
  const defaults = defaultView ? [["default", "Default view"]] : [];
  for (const [id, title] of [...defaults, ["auto", "Auto view"], ["face", "Face-on"], ["above", "Above"],
    ["side", "Side"], ["flip", "Other side"], ["roll-left", "Roll left ↶"],
    ["roll-right", "Roll right ↷"], ["fit", "Fit scan"]]) {
    const button = document.createElement("button"); button.type = "button";
    button.dataset.scanView = id; button.textContent = title;
    if (id === "default") button.title = "Restore the whole arch's front view, position and zoom";
    button.onclick = () => onView(id); bar.append(button);
  }
  const note = document.createElement("small");
  note.textContent = "View changes only. Auto view estimates a useful angle; use Other side or Roll if needed.";
  if (!compact) bar.append(note);
  before.before(bar);
  return bar;
}
