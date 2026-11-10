import { el, state } from "./state.js";
import { applySampleRootBoneFixture, prepareSampleSegmentation } from "./sample.js";
import { comparisonTemplate } from "./scan_comparison_template.js";
import { createScanComparison } from "./scan_comparison_viewer.js";
import { inputValidationText, loadObservedPair, revealFraction } from "./scan_comparison_data.js";

let mounted = false, viewer = null, request = null, session = null, startedPlanning = false;

export function observedSampleActive() {
  return state.sample.active && state.sample.view === "observed";
}

function setReveal(value) {
  const percent = revealFraction(value) * 100;
  el("comparisonReveal").value = String(percent);
  el("comparisonReveal").setAttribute("aria-valuetext", `${Math.round(percent)}% week 7 revealed; not elapsed time`);
  el("comparisonPercent").textContent = `${Math.round(percent)}%`;
  el("comparisonDivider").hidden = percent === 0 || percent === 100;
  el("comparisonDivider").style.left = `${100 - percent}%`;
  el("comparisonBefore").hidden = percent === 100;
  el("comparisonAfter").hidden = percent === 0;
  viewer?.setReveal(percent);
}

function setReady(ready) {
  el("sampleComparison").dataset.ready = String(ready);
  el("comparisonReveal").disabled = !ready;
  for (const button of el("sampleComparison").querySelectorAll(".comparison-toolbar button, .comparison-endpoints button")) {
    button.disabled = !ready;
  }
}

async function loadArch() {
  request?.abort();
  const pending = new AbortController();
  request = pending;
  setReady(false);
  viewer?.clear();
  el("comparisonRetry").hidden = true;
  el("comparisonStatus").textContent = "Loading and verifying the two original scans…";
  el("comparisonValidation").textContent = "Loading the scan validation record…";
  try {
    viewer ||= createScanComparison(el("comparisonCanvas"), {
      onFocus: () => { el("comparisonStatus").textContent = "Region focused. Alternate visits to inspect this area; this viewer does not compute per-tooth displacement."; },
    });
    const pair = await loadObservedPair(el("comparisonArch").value, { signal: pending.signal });
    if (pending.signal.aborted || !observedSampleActive()) return;
    viewer.setPair(pair);
    el("comparisonBefore").textContent = `${pair[0].label} · ${pair[0].date}`;
    el("comparisonAfter").textContent = `${pair[1].label} · ${pair[1].date}`;
    el("comparisonValidation").textContent = inputValidationText(pair.every(scan => scan.validation) ? pair[0].validation : null);
    setReveal(50);
    setReady(true);
    el("comparisonStatus").textContent = "Original scan pair loaded and hashes verified. The reveal uses display orientation and centering; per-tooth displacement is not computed.";
  } catch (error) {
    if (pending.signal.aborted) return;
    viewer?.clear();
    el("comparisonDivider").hidden = true;
    el("comparisonStatus").textContent = `Comparison unavailable: ${error.message}`;
    el("comparisonValidation").textContent = "The scan validation record could not be loaded with a complete pair.";
    el("comparisonRetry").hidden = false;
  }
}

function mount(renderAll) {
  const modes = document.createElement("div");
  modes.id = "sampleViewModes";
  modes.className = "sample-view-modes";
  modes.setAttribute("role", "group");
  modes.setAttribute("aria-label", "Sample example mode");
  modes.innerHTML = `<button type="button" data-sample-view="observed">Observed scan comparison</button>
    <button type="button" data-sample-view="simulation">Simulated planning demo</button>
    <p id="sampleSimulationNote" hidden>Simulation only — these stages are not USER_ONE’s observed tooth movements.</p>`;
  const panel = document.createElement("section");
  panel.id = "sampleComparison";
  panel.innerHTML = comparisonTemplate;
  el("viewerBlock").prepend(modes, panel);
  modes.addEventListener("click", async event => {
    const button = event.target.closest("[data-sample-view]");
    if (!button) return;
    state.sample.view = button.dataset.sampleView;
    renderAll();
    if (state.sample.view === "simulation" && !startedPlanning) {
      startedPlanning = true;
      const current = state.segmentation;
      await applySampleRootBoneFixture();
      if (state.sample.active && state.segmentation === current) await prepareSampleSegmentation();
      renderAll();
    }
  });
  el("comparisonArch").addEventListener("change", loadArch);
  el("comparisonRetry").addEventListener("click", loadArch);
  el("comparisonReveal").addEventListener("input", event => setReveal(event.target.value));
  for (const [id, value] of [["comparisonBaseline", 0], ["comparisonSplit", 50], ["comparisonWeek7", 100]]) {
    el(id).addEventListener("click", () => setReveal(value));
  }
  el("comparisonZoomIn").addEventListener("click", () => viewer?.zoom(1.25));
  el("comparisonZoomOut").addEventListener("click", () => viewer?.zoom(0.8));
  el("comparisonReset").addEventListener("click", () => viewer?.setView());
  panel.querySelectorAll("[data-comparison-view]").forEach(button => {
    button.addEventListener("click", () => viewer?.setView(button.dataset.comparisonView));
  });
  const divider = el("comparisonDivider");
  divider.addEventListener("pointerdown", event => {
    if (el("comparisonReveal").disabled) return;
    event.preventDefault();
    divider.setPointerCapture(event.pointerId);
  });
  divider.addEventListener("pointermove", event => {
    if (!divider.hasPointerCapture(event.pointerId)) return;
    const box = el("comparisonCanvas").getBoundingClientRect();
    // Keep a tiny visible handle at the extremes during a drag.
    setReveal(Math.min(99.9, Math.max(0.1, 100 * (1 - (event.clientX - box.left) / box.width))));
  });
  divider.addEventListener("pointerup", event => {
    if (divider.hasPointerCapture(event.pointerId)) divider.releasePointerCapture(event.pointerId);
  });
  mounted = true;
}

export function renderSampleComparison(renderAll) {
  if (!mounted) mount(renderAll);
  const observed = observedSampleActive();
  document.body.dataset.sampleView = state.sample.active ? state.sample.view : "";
  el("sampleViewModes").hidden = !state.sample.active;
  el("sampleComparison").hidden = !observed;
  el("viewerBlock").classList.toggle("sample-observed", observed);
  el("sampleSimulationNote").hidden = !state.sample.active || observed;
  el("sampleViewModes").querySelectorAll("[data-sample-view]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.sampleView === state.sample.view));
  });
  if (session !== state.segmentation || !state.sample.active) {
    session = state.segmentation;
    startedPlanning = false;
  }
  if (observed && !viewer && !request) loadArch();
  if (observed) viewer?.resize();
  else {
    request?.abort();
    request = null;
    viewer?.dispose();
    viewer = null;
  }
}
