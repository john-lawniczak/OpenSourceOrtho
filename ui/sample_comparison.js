import { el, state } from "./state.js";
import { applySampleRootBoneFixture, prepareSampleSegmentation } from "./sample.js";
import { comparisonTemplate } from "./scan_comparison_template.js";
import { createHistoryViewer } from "./scan_history_viewer.js";
import { loadObservedPair } from "./scan_comparison_data.js";
import { loadMotionPreview } from "./scan_motion_data.js";
import { renderMotionControls } from "./scan_motion_controls.js";
import { proximitySummary } from "./proximity_summary.js";
import { historyFrame } from "./scan_history.js";

let motion = null, motionError = "", selectedTooth = "", endpointEstimate = false;
let pair = [], week = 1, arch = "both", ready = false, timing = "uniform";
let mounted = false, viewer = null, request = null, session = null, startedPlanning = false;

export function observedSampleActive() {
  return state.sample.active && state.sample.view === "observed";
}

function setWeek(value) {
  week = value;
  const frame = historyFrame(week, pair, motion, endpointEstimate, timing);
  el("comparisonWeekLabel").textContent = `Week ${week} of 7`;
  el("comparisonVisit").textContent = frame.kind === "estimated" ? `Week ${week} · SIMULATED ESTIMATE`
    : frame.scan ? `${frame.scan.label} · ${frame.scan.date} · observed scan` : `Week ${week} · estimate unavailable`;
  el("comparisonMissing").hidden = !ready || frame.kind !== "unavailable";
  el("comparisonMissingTitle").textContent = `Week ${week} estimate unavailable`;
  el("comparisonCanvas").style.visibility = ready && frame.kind === "unavailable" ? "hidden" : "visible";
  el("comparisonHelp").hidden = frame.kind === "unavailable";
  viewer?.setFrame(frame);
  viewer?.selectTooth(selectedTooth);
  renderMotionControls(motion, selectedTooth, frame, motionError);
  el("comparisonTiming").value = timing;
  el("comparisonTiming").disabled = !ready || !motion;
  el("comparisonProximity").textContent = motion ? proximitySummary(motion.contact_reports || [], week, timing) : "";
  el("sampleComparison").dataset.frameKind = frame.kind;
  el("sampleComparison").querySelectorAll("[data-comparison-week]").forEach(button => {
    const value = Number(button.dataset.comparisonWeek);
    if (value === 1 || value === 7) return;
    button.querySelector("small").textContent = motion ? "Estimated" : "Unavailable";
    button.setAttribute("aria-label", `Week ${value}, ${motion ? "simulated estimate" : "estimate unavailable"}`);
  });
  updateControls();
  if (ready) el("comparisonStatus").textContent = frame.kind === "estimated"
    ? `Week ${week}: estimated tooth poses, ${(frame.fraction * 100).toFixed(0)}% through the fitted endpoint motion. No movement exaggeration.`
    : frame.scan ? `Original scan · file integrity verified.${motion ? " Week 7 uses an estimated whole-arch alignment." : ""}`
      : `Week ${week}: motion preview unavailable. The original endpoint scans remain available.`;
  if (ready && frame.kind === "estimated" && motionError) el("comparisonStatus").textContent += ` ${motionError}. Only available arch estimates are displayed.`;
}

function updateControls() {
  el("sampleComparison").querySelectorAll("[data-comparison-week]").forEach(button => {
    button.disabled = !ready;
    button.setAttribute("aria-current", Number(button.dataset.comparisonWeek) === week ? "step" : "false");
  });
  el("comparisonPrevious").disabled = !ready || week === 1;
  el("comparisonNext").disabled = !ready || week === 7;
  el("sampleComparison").querySelectorAll(".comparison-toolbar button, .comparison-zoom button").forEach(button => {
    button.disabled = !button.dataset.comparisonArch && (!ready || historyFrame(week, pair, motion, endpointEstimate).kind === "unavailable");
    if (button.dataset.comparisonArch) button.setAttribute("aria-pressed", String(button.dataset.comparisonArch === arch));
  });
}

function setReady(value) {
  ready = value;
  el("sampleComparison").dataset.ready = String(ready);
  updateControls();
}

async function loadArch() {
  request?.abort();
  const pending = new AbortController();
  request = pending;
  setReady(false);
  pair = []; motion = null; motionError = ""; selectedTooth = "";
  setWeek(week);
  viewer?.clear();
  el("comparisonRetry").hidden = true;
  el("comparisonStatus").textContent = "Loading and verifying the two original scans…";
  try {
    viewer ||= createHistoryViewer(el("comparisonCanvas"), {
      onFocus: () => { el("comparisonStatus").textContent = "Region focused. Step through weeks to inspect the estimated motion."; },
      onTooth: tooth => { selectedTooth = tooth; setWeek(week); },
    });
    const bundles = await Promise.all((arch === "both" ? ["upper", "lower"] : [arch]).map(async name => {
      const scans = await loadObservedPair(name, { signal: pending.signal });
      let preview = null;
      try { preview = await loadMotionPreview(scans, { signal: pending.signal }); }
      catch (error) { if (!pending.signal.aborted) motionError = `${name} motion preview unavailable: ${error.message}`; }
      return { pair: scans, motion: preview };
    }));
    if (pending.signal.aborted || !observedSampleActive()) return;
    pair = bundles[0].pair;
    const available = bundles.filter(item => item.motion);
    motion = available.length ? { teeth: available.flatMap(item => item.motion.teeth),
      simulation: available[0].motion.simulation,
      contact_reports: available.map(item => ({ arch: item.pair[0].arch, simulation: item.motion.simulation })) } : null;
    viewer.setPairs(bundles);
    setReady(true);
    setWeek(week);
  } catch (error) {
    if (pending.signal.aborted) return;
    viewer?.clear();
    pair = []; motion = null;
    setReady(false);
    setWeek(week);
    el("comparisonStatus").textContent = `Comparison unavailable: ${error.message}`;
    el("comparisonRetry").hidden = false;
  }
}

function mount(renderAll) {
  const modes = document.createElement("div");
  modes.id = "sampleViewModes";
  modes.className = "sample-view-modes";
  modes.setAttribute("role", "group");
  modes.setAttribute("aria-label", "Sample example mode");
  modes.innerHTML = `<button type="button" data-sample-view="observed">Scan history</button>
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
  panel.querySelectorAll("[data-comparison-arch]").forEach(button => {
    button.addEventListener("click", () => {
      if (arch === button.dataset.comparisonArch) return;
      arch = button.dataset.comparisonArch;
      loadArch();
    });
  });
  el("comparisonTiming").addEventListener("change", event => { timing = event.target.value; setWeek(week); });
  el("comparisonRetry").addEventListener("click", loadArch);
  el("comparisonMotionRetry").addEventListener("click", loadArch);
  el("comparisonTooth").addEventListener("change", event => { selectedTooth = event.target.value; setWeek(week); });
  el("comparisonFocusTooth").addEventListener("click", () => viewer?.focusTooth(selectedTooth));
  el("comparisonEndpointFit").addEventListener("click", () => { endpointEstimate = !endpointEstimate; setWeek(week); });
  panel.querySelectorAll("[data-comparison-week]").forEach(button => {
    button.addEventListener("click", () => setWeek(Number(button.dataset.comparisonWeek)));
  });
  el("comparisonPrevious").addEventListener("click", () => setWeek(week - 1));
  el("comparisonNext").addEventListener("click", () => setWeek(week + 1));
  el("comparisonZoomIn").addEventListener("click", () => viewer?.zoom(1.25));
  el("comparisonZoomOut").addEventListener("click", () => viewer?.zoom(0.8));
  el("comparisonReset").addEventListener("click", () => { viewer?.setView(); setWeek(week); });
  panel.querySelectorAll("[data-comparison-view]").forEach(button => {
    button.addEventListener("click", () => { viewer?.setView(button.dataset.comparisonView); setWeek(week); });
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
    if (!state.sample.active) { week = 1; arch = "both"; endpointEstimate = false; timing = "uniform"; }
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
