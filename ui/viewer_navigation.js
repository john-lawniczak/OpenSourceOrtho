import * as THREE from "./vendor/three.module.js";

// Camera gestures only; tooth selection and edits remain separate actions.
export function mountViewerNavigation(host, getControls, onFocus) {
  const bar = document.createElement("div");
  bar.className = "viewer-navigation-modes"; bar.setAttribute("role", "group"); bar.setAttribute("aria-label", "Move the view");
  bar.innerHTML = '<button type="button" data-viewer-drag="rotate" aria-pressed="true">↻ Rotate</button><button type="button" data-viewer-drag="pan" aria-pressed="false">✥ Pan</button><button type="button" data-viewer-focus disabled>Focus selected tooth</button><small>Drag to rotate · scroll/pinch to zoom · right-drag to pan</small>';
  host.before(bar);
  let mode = "rotate";
  function apply() {
    const controls = getControls(), pan = mode === "pan";
    controls.screenSpacePanning = true;
    controls.mouseButtons.LEFT = pan ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.touches.ONE = pan ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
  }
  bar.querySelector("[data-viewer-focus]").onclick = () => onFocus?.();
  bar.addEventListener("click", event => {
    const button = event.target.closest("[data-viewer-drag]"); if (!button) return;
    mode = button.dataset.viewerDrag; apply();
    bar.querySelectorAll("[data-viewer-drag]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
    bar.querySelector("small").textContent = mode === "pan" ? "Drag to pan · scroll/pinch to zoom · choose Rotate to turn the scan" : "Drag to rotate · scroll/pinch to zoom · right-drag to pan";
  });
  apply();
  return { element: bar, apply, setFocusAvailable: enabled => { bar.querySelector("[data-viewer-focus]").disabled = !enabled; }, get mode() { return mode; }, dispose: () => bar.remove() };
}
