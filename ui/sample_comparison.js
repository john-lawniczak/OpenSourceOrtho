import { el, state } from "./state.js";
import { prepareSampleSegmentation } from "./sample.js";
import { comparisonTemplate } from "./scan_comparison_template.js";
import { createHistoryViewer } from "./scan_history_viewer.js";
import { loadWeekEighteenScan } from "./scan_week_eighteen.js";
import { loadObservedPair } from "./scan_comparison_data.js";
import { loadMotionPreview } from "./scan_motion_data.js";
import { renderMotionControls } from "./scan_motion_controls.js";
import { proximitySummary } from "./proximity_summary.js";
import { historyFrame } from "./scan_history.js";
import { sampleViewForStep } from "./sample_view.js";

let motion = null, motionError = "", selectedTooth = "", endpointEstimate = false;
let pair = [], week = 1, arch = "both", ready = false, timing = "uniform";
let visitRequest = null, visitError = "";
let mounted = false, viewer = null, request = null, session = null, preparedSession = null;

export function observedSampleActive() {
  return state.sample.active && sampleViewForStep(state.sample,state.userMode,state.guided.step) === "observed";
}

function setWeek(value) {
  week = value;
  el("sampleComparison").dataset.week = String(week);
  if (week !== 18) { visitRequest?.abort(); visitRequest = null; }
  const frame = historyFrame(week, pair, motion, endpointEstimate, timing);
  el("comparisonWeekLabel").textContent = `Week ${week} of 18`;
  el("comparisonVisit").textContent = frame.kind === "estimated" ? `Week ${week} · SIMULATED ESTIMATE`
    : frame.scan ? `${frame.scan.label} · ${frame.scan.date} · observed scan` : `Week ${week} · estimate unavailable`;
  el("comparisonMissing").hidden = !ready || frame.kind !== "unavailable";
  el("comparisonMissingTitle").textContent = `Week ${week} estimate unavailable`;
  el("comparisonCanvas").style.visibility = ready && frame.kind === "unavailable" ? "hidden" : "visible";
  el("comparisonHelp").hidden = frame.kind === "unavailable";
  viewer?.setFrame(frame);
  viewer?.selectTooth(selectedTooth);
  renderMotionControls(week <= 7 ? motion : null, selectedTooth, frame, week <= 7 ? motionError : "");
  if (week > 7) el("comparisonMatchDetail").textContent = "Week 18: observed model scans. Painting and a new endpoint fit are needed for weeks 1–18; damaged or unmatched regions will remain uncertain.";
  el("comparisonTiming").value = timing;
  el("comparisonTiming").disabled = !ready || !motion || week > 7;
  el("comparisonProximity").textContent = motion && week <= 7 ? proximitySummary(motion.contact_reports || [], week, timing) : "";
  el("sampleComparison").dataset.frameKind = frame.kind;
  el("sampleComparison").querySelectorAll("[data-comparison-week]").forEach(button => {
    const value = Number(button.dataset.comparisonWeek);
    if (value === 1 || value === 7 || value === 18) return;
    button.dataset.scanKind = value < 7 && motion ? "estimated" : "unavailable";
    button.querySelector("small").textContent = value > 7 ? "Not fitted" : motion ? "Estimated" : "Unavailable";
    button.setAttribute("aria-label", `Week ${value}, ${motion && value < 7 ? "simulated estimate" : "estimate unavailable"}`);
  });
  updateControls();
  if (ready) el("comparisonStatus").textContent = frame.kind === "estimated"
    ? `Week ${week}: estimated tooth poses, ${(frame.fraction * 100).toFixed(0)}% through the fitted endpoint motion. No movement exaggeration.`
    : frame.scan ? `Original scan · file integrity verified.${motion ? " Week 7 uses an estimated whole-arch alignment." : ""}`
      : `Week ${week}: motion preview unavailable. The original endpoint scans remain available.`;
  if (ready && week === 18) {
    el("comparisonMissingTitle").textContent = visitError ? "Week 18 scan unavailable" : "Loading week 18 scans…";
    el("comparisonStatus").textContent = pair[2] ? "Week 18 original scans · file integrity verified. Model chips are reported; scale and cross-visit alignment are unverified. Display placement is not a measured bite."
      : visitError || "Loading and verifying week 18 scans…";
    if (!pair[2] && !visitRequest && !visitError) void loadWeekEighteen();
  }
  if (ready && frame.kind === "estimated" && motionError) el("comparisonStatus").textContent += ` ${motionError}. Only available arch estimates are displayed.`;
}

async function loadWeekEighteen() {
  const pending = new AbortController(), currentViewer = viewer;
  visitRequest = pending;
  try {
    const scans = await Promise.all((arch === "both" ? ["upper", "lower"] : [arch])
      .map(name => loadWeekEighteenScan(name, { signal: pending.signal })));
    if (pending.signal.aborted || viewer !== currentViewer || !state.sample.active) return;
    viewer.setObservedVisit(scans); pair[2] = scans[0];
    if (week === 18) setWeek(week);
  } catch (error) {
    if (pending.signal.aborted || viewer !== currentViewer) return;
    visitError = error.message;
    if (week === 18) { setWeek(week); el("comparisonRetry").hidden = false; }
  } finally { if (visitRequest === pending) visitRequest = null; }
}

function updateControls() {
  el("sampleComparison").querySelectorAll("[data-comparison-week]").forEach(button => {
    button.disabled = !ready;
    button.setAttribute("aria-current", Number(button.dataset.comparisonWeek) === week ? "step" : "false");
  });
  el("comparisonPrevious").disabled = !ready || week === 1;
  el("comparisonNext").disabled = !ready || week === 18;
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
  request?.abort(); visitRequest?.abort(); visitRequest = null; visitError = "";
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
    if (pending.signal.aborted || !state.sample.active) return;
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
  } finally { if(request===pending) request=null; }
}

function mount(renderAll) {
  const modes = document.createElement("div");
  modes.id = "sampleViewModes";
  modes.className = "sample-view-modes";
  modes.setAttribute("role", "group");
  modes.setAttribute("aria-label", "Sample example mode");
  modes.innerHTML = `<button type="button" data-sample-view="observed">Scan history</button>
    <button type="button" data-sample-view="simulation">Explore individual teeth</button>
    <p id="sampleSimulationNote" hidden>Exploratory workspace — painted regions are contributor drafts. Proposed stages are separate from observed history. Week 7 arches are arranged for viewing; their displayed gap is not a measured bite.</p>
    <label id="sampleVisitControl" hidden>Painted scan <select id="samplePaintedVisit"><option value="progress-01">Week 7 · latest saved painting</option><option value="initial">Week 1 · baseline painting</option></select></label>
    <button id="sampleReloadPainting" type="button" hidden>Reload saved painting</button>`;
  const panel = document.createElement("section");
  panel.id = "sampleComparison";
  panel.innerHTML = comparisonTemplate;
  el("viewerBlock").prepend(modes, panel);
  el("highlightScanWeeks").addEventListener("change", event => {
    panel.classList.toggle("scan-highlights-off", !event.target.checked);
  });
  el("highlightEstimatedWeeks").addEventListener("change", event => {
    panel.classList.toggle("estimate-highlights-off", !event.target.checked);
  });
  modes.addEventListener("click", async event => {
    const button = event.target.closest("[data-sample-view]");
    if (!button) return;
    state.sample.view = button.dataset.sampleView;
    if (state.sample.view === "observed" && state.userMode === "simple" && sampleViewForStep(state.sample,state.userMode,state.guided.step) !== "observed") state.guided.step = "plan";
    renderAll();
    if (state.sample.view === "simulation" && !state.segmentation.applied && !state.segmentation.busy) {
      const pending = prepareSampleSegmentation({ allowFallback: true });
      renderAll(); await pending; renderAll();
    }
  });
  async function reloadPainting() {
    if ((state.manualEdit.undoStack?.length || state.goalPreview) && !window.confirm("Reloading painted scans clears exploratory edits. Continue?")) {
      el("samplePaintedVisit").value = state.sample.visit; return;
    }
    const pending = prepareSampleSegmentation({ visit: el("samplePaintedVisit").value });
    renderAll(); await pending; renderAll();
  }
  el("samplePaintedVisit").addEventListener("input", reloadPainting);
  el("sampleReloadPainting").addEventListener("click", reloadPainting);
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
  const view=sampleViewForStep(state.sample,state.userMode,state.guided.step);
  if (state.sample.active && view === "simulation") {
    if (!state.segmentation.applied && !state.segmentation.busy && preparedSession !== state.segmentation) {
      preparedSession=state.segmentation; prepareSampleSegmentation({ allowFallback: true }).then(renderAll);
    }
  }
  const observed = observedSampleActive();
  document.body.dataset.sampleView = state.sample.active ? view : "";
  el("sampleViewModes").hidden = !state.sample.active;
  el("sampleComparison").hidden = !observed;
  el("viewerBlock").classList.toggle("sample-observed", observed);
  el("sampleSimulationNote").hidden = !state.sample.active || observed;
  el("sampleVisitControl").hidden = !state.sample.active || observed;
  el("sampleReloadPainting").hidden = !state.sample.active || observed;
  el("samplePaintedVisit").value = state.sample.visit || "progress-01";
  el("samplePaintedVisit").disabled = state.segmentation.busy;
  el("sampleReloadPainting").disabled = state.segmentation.busy;
  el("sampleViewModes").querySelectorAll("[data-sample-view]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.sampleView === view));
  });
  if (session !== state.segmentation || !state.sample.active) {
    session = state.segmentation;
    if (!state.sample.active) { week = 1; arch = "both"; endpointEstimate = false; timing = "uniform"; }
  }
  if (observed && !viewer && !request) loadArch();
  if (observed) viewer?.resize();
  else if (!state.sample.active) {
    request?.abort(); visitRequest?.abort(); visitRequest = null;
    request = null;
    viewer?.dispose();
    viewer = null;
  }
}
