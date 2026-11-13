import { state } from "./state.js";
import { sampleViewForStep } from "./sample_view.js";

let dialog, frame, returnFocus;
export function openPrecisionWorkspace(path = "./region-review.html") {
  const url = new URL(path, location.href);
  if (url.origin !== location.origin || !url.pathname.endsWith('/region-review.html')) return;
  if (!dialog) {
    dialog = document.createElement("dialog"); dialog.className = "precision-dialog";
    dialog.setAttribute("aria-label", "Edit Tooth Precision");
    const header = document.createElement("header");
    const back = document.createElement("button"); back.type = "button"; back.id = "precisionBack";
    back.onclick = closePrecisionWorkspace;
    const title = document.createElement("strong"); title.textContent = "Edit Tooth Precision";
    header.append(back, title);
    frame = document.createElement("iframe"); frame.title = "Tooth precision painting workspace";
    frame.onload = () => {
      frame.contentDocument.documentElement.style.colorScheme = document.body.dataset.theme || "light";
    };
    dialog.append(header, frame); document.body.append(dialog);
    dialog.addEventListener("cancel", event => { event.preventDefault(); closePrecisionWorkspace(); });
    window.addEventListener("message", event => {
      if (event.origin === location.origin && event.source === frame.contentWindow && event.data?.type === "precision-return") closePrecisionWorkspace();
    });
  }
  returnFocus = document.activeElement;
  const names = { upload: "Upload", plan: "Explore your teeth", details: "Your plan", preview: "3D preview" };
  dialog.querySelector("button").textContent = `← Back to ${state.activeStep === "notes" ? "saved notes" : names[state.guided.step] || "stages"}`;
  url.searchParams.set("embedded", "1");
  if (state.sample.active) url.searchParams.set("sample", "1");
  frame.src = url.href; dialog.showModal(); dialog.querySelector("button").focus();
}
function closePrecisionWorkspace() {
  const canLeave = frame.contentWindow.confirmPrecisionExit;
  if (canLeave && !canLeave()) return;
  dialog.close(); frame.src = "about:blank";
  returnFocus?.focus({ preventScroll: true });
  document.dispatchEvent(new Event("precision-workspace-closed"));
}

// Preserve the current plan, camera and scroll instead of navigating away.
document.addEventListener("click", event => {
  const link = event.target.closest?.('a[href*="region-review.html"]');
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.button) return;
  event.preventDefault();
  const params = new URL(link.href).searchParams;
  if (params.has("baseline") || params.has("edit")) { openPrecisionWorkspace(link.href); return; }
  if (state.sample.active) {
    const arch = document.getElementById("boundaryArch")?.value || "upper";
    const visit = sampleViewForStep(state.sample,state.userMode,state.guided.step) === "observed" && document.getElementById("sampleComparison")?.dataset.week === "18" ? "progress-02" : state.sample.visit || "progress-01";
    openPrecisionWorkspace(`./region-review.html?baseline=${arch}&visit=${visit}${visit === "progress-02" ? `&capture=${arch === "upper" ? "upper-clean" : "fusion-h-4"}` : ""}`);
  } else {
    const openScan = document.getElementById("openBoundaryEditor");
    if (state.scanSources.length && document.getElementById("boundaryArch")?.value && !openScan?.disabled) openScan.click();
    else openPrecisionWorkspace(link.href);
  }
});
