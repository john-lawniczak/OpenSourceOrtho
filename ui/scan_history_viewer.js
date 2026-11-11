import { createScanComparison } from "./scan_comparison_viewer.js";

// Separate arch viewports share week and zoom commands, not a fabricated bite registration.
export function createHistoryViewer(host, options = {}) {
  let views = [];
  function clear() {
    views.forEach(item => item.viewer.dispose());
    views = [];
    host.replaceChildren();
  }
  return {
    setPairs(bundles) {
      clear();
      host.dataset.archCount = String(bundles.length);
      for (const bundle of bundles) {
        const section = document.createElement("section");
        section.className = "comparison-arch-surface";
        const label = document.createElement("span");
        label.className = "comparison-arch-label";
        label.textContent = bundle.pair[0].arch === "upper" ? "Upper teeth" : "Lower teeth";
        const canvas = document.createElement("div");
        canvas.className = "comparison-arch-canvas";
        canvas.dataset.arch = bundle.pair[0].arch;
        section.append(label, canvas); host.append(section);
        const viewer = createScanComparison(canvas, options);
        viewer.setPair(bundle.pair, bundle.motion);
        views.push({ ...bundle, viewer, label });
      }
    },
    setFrame(frame) {
      views.forEach(item => {
        const unavailable = frame.index === 2 && !item.motion;
        item.viewer.setFrame({ ...frame, index: unavailable ? null : frame.index });
        item.label.textContent = `${item.pair[0].arch === "upper" ? "Upper" : "Lower"} teeth${unavailable ? " · estimate unavailable" : ""}`;
      });
    },
    selectTooth(id) { views.forEach(item => item.viewer.selectTooth(item.motion?.teeth.some(t => t.tooth === id) ? id : "")); },
    focusTooth(id) { views.forEach(item => item.viewer.focusTooth(id)); },
    zoom(factor) { views.forEach(item => item.viewer.zoom(factor)); },
    setView(view) { views.forEach(item => item.viewer.setView(view)); },
    resize() { views.forEach(item => item.viewer.resize()); },
    clear, dispose: clear,
  };
}
