export function mountScanViewToolbar(before, onView) {
  const bar = document.createElement("div");
  bar.className = "scan-view-controls"; bar.setAttribute("aria-label", "Scan view controls");
  const label = document.createElement("span"); label.textContent = "View"; bar.append(label);
  for (const [id, title] of [["auto", "Auto view"], ["face", "Face-on"], ["above", "Above"],
    ["side", "Side"], ["flip", "Other side"], ["roll-left", "Roll left ↶"],
    ["roll-right", "Roll right ↷"], ["fit", "Fit scan"]]) {
    const button = document.createElement("button"); button.type = "button";
    button.dataset.scanView = id; button.textContent = title;
    button.onclick = () => onView(id); bar.append(button);
  }
  const note = document.createElement("small");
  note.textContent = "View changes only. Auto view estimates a useful angle; use Other side or Roll if needed.";
  bar.append(note); before.before(bar);
  return bar;
}
