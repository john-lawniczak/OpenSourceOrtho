import { renderBoundaryEntry } from "./uploaded_boundary_entry.js";
import { focusedTeeth, renderFocusTeeth } from "./plan_focus.js";
import { renderChat } from "./chat_view.js";
export { renderChat } from "./chat_view.js";
import { buildViewerScanSources } from "./scan_formats.js";
import {
  availabilityLabels,
  el,
  evaluatePlan,
  iprContactPairs,
  numberValue,
  state,
  toothPositions,
} from "./state.js";
import {
  archFromTooth,
  escapeHtml,
  framePoseTotals,
  inferArchFromName,
  toothKind,
} from "./core.js";
import { createViewer } from "./viewer3d.js";
import { planJson } from "./plan.js";
import { renderGuided } from "./guided.js";
import { scaleConfirmed, targetFor, targetMagnitudeMm } from "./manual_edit.js";
import { CONTROL_AXES, CONTROL_STEPS, controlGate } from "./direct_controls.js";
import { formatScaleStatus } from "./scale.js";
import { registeredOffsetForViewer } from "./proximity.js";
import { renderSetupCompare, scheduleSetupCompare } from "./setup_compare.js";
import { renderSegmentation } from "./segmentation_render.js";
import { renderPrintExport } from "./print_export.js";
import { renderTrustStatus } from "./trust_status.js";
import { createEvaluationRunner } from "./evaluation_runner.js";
import { renderAnatomyReview } from "./anatomy_render.js";
import { observedSampleActive, renderSampleComparison } from "./sample_comparison.js";

let viewer = null;
let viewerFailed = false;
// One-shot request to re-frame the camera once the next evaluation has populated
// the scene. Used when a new scene becomes visible (sample screen, guided 3D
// step) where the viewer may have been sized while hidden or framed for a
// different scene. It is honored after the async evaluation renders, so the fit
// uses the real container size and the new geometry.
let pendingRefit = false;

export function acceptGoalEvaluation(result) {
  state.lastEval = result;
  scheduleEvaluate.prime(planJson(), result);
}

export function requestViewerRefit() {
  pendingRefit = true;
}

function formatWeek(value) {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function stagePhaseText(result, stageIndex) {
  if (!result?.timeline) return `Stage ${stageIndex}`;
  const totalAligners = Math.max(1, Number(result.timeline.stage_count || result.frames?.length || 1));
  const alignerNumber = Math.min(totalAligners, stageIndex + 1);
  const wearDays = Math.max(0, Number(result.timeline.wear_interval_days || 0));
  const weekStart = (stageIndex * wearDays) / 7;
  const weekEnd = ((stageIndex + 1) * wearDays) / 7;
  return `Aligner ${alignerNumber} of ${totalAligners} · Weeks ${formatWeek(weekStart)}-${formatWeek(weekEnd)}`;
}

function updateStagePhase(result = state.lastEval) {
  result = state.goalPreview?.evaluation || result;
  const slider = el("stageSlider");
  const stageIndex = Number(slider.value || 0);
  el("stageValue").textContent = String(stageIndex);
  if (!result?.timeline) {
    el("stagePhase").textContent = "Aligner timeline unavailable";
    return;
  }
  el("stagePhase").textContent = stagePhaseText(result, stageIndex);
}

function ensureViewer() {
  if (viewer || viewerFailed) return viewer;
  try {
    viewer = createViewer(el("viewer3d"));
    viewer.setSelectionHandler((tooth) => {
      state.manualEdit.selectedTooth = tooth;
      renderAll();
    });
  } catch (error) {
    viewerFailed = true;
    el("viewer3d").textContent = "3D preview could not start. Try reloading in a browser with WebGL enabled.";
    el("viewerZoom").hidden = true;
    el("archCanvas").hidden = true;
    state.dim = "3d";
  }
  return viewer;
}

// Keep the public workspace on the source-based 3D preview.
export function setDimension() {
  state.dim = "3d";
  el("viewer3d").hidden = false;
  el("archCanvas").hidden = true;
  el("viewerZoom").hidden = viewerFailed;
  renderAll();
}

// Zoom/recenter hooks for the on-screen 3D controls. No-ops outside 3D.
export function zoomViewer(factor) {
  if (state.dim !== "3d") return;
  ensureViewer()?.zoomBy(factor);
}

export function recenterViewer() {
  if (state.dim !== "3d") return;
  ensureViewer()?.recenter();
}

// Demo crowns are static-served per tooth class so the Guided demo exercises the
// real mesh-loading path (and shows rounded crowns) without a registered scan.
function demoRenderMeshes() {
  return Object.keys(state.demoInitialOffsets || {}).map((tooth) => ({
    tooth,
    url: `/demo-meshes/${toothKind(tooth)}.stl`,
  }));
}

// Status line under the 3D viewer for a loaded scan: which movement layer is
// active, with an in-progress note while the on-device segmenter is running
// (e.g. the sample test case preparing its per-tooth teeth).
function scanStatusText(count, movingFragments) {
  if (!count) return "Your scan could not be displayed.";
  if (movingFragments) return "Showing your scan with reviewed per-tooth fragments moving in 3D.";
  if (state.segmentation.busy) {
    return "Showing your scan. Identifying tooth regions locally…";
  }
  return "Showing your scan. Review tooth regions to enable individual selection.";
}

function updateViewer(result) {
  if (observedSampleActive()) { renderBoundaryEntry([]); return; }
  result = state.goalPreview?.evaluation || result;
  if (state.dim !== "3d") return;
  const v = ensureViewer();
  if (!v) return;
  v.resize();
  const allScanSources = buildViewerScanSources(state.files, state.scanSources, inferArchFromName);
  renderBoundaryEntry(allScanSources);
  const scanSources = filterScanSources(allScanSources);
  v.setVisibleArchFilter(state.scanArchFilter);
  if (allScanSources.length) {
    v.loadScanSources(allScanSources).then(({ loaded, stale }) => {
      if (stale || (state.goalPreview?.evaluation || state.lastEval) !== result) return;
      const movingFragments = Boolean(
        result.render_meshes?.some((item) => item.source === "model-generated" && toothMatchesArch(item.tooth)),
      );
      state.scanRenderStatus = scanStatusText(scanSources.length, movingFragments);
      renderScanStatus();
      if (loaded && (state.goalPreview?.evaluation || state.lastEval) === result) updateViewer(result);
    }).catch(() => {
      state.scanRenderStatus = "Your scan could not be displayed.";
      renderScanStatus();
    });
  } else {
    v.loadScanSources([]);
    state.scanRenderStatus = state.useDemoMeshes
      ? "Simulated sample teeth — drag the stage slider to watch them move."
      : "No scan loaded yet; the preview uses simple placeholder teeth.";
    renderScanStatus();
  }
  // Applied segmentation yields real per-tooth crown fragments (scan-space,
  // source "model_generated"). With a scan loaded, render those moving at their
  // true positions; otherwise fall back to centered class/demo meshes positioned
  // on the schematic arch.
  const scanLoaded = scanSources.length > 0;
  // Segmentation links carry MeshProvenance.MODEL_GENERATED, whose serialized
  // value is "model-generated" (hyphen). Match that exact string.
  const applied = state.segmentation.applied?.tooth_meshes;
  const draft = !applied && state.segmentation.proposal?.teeth;
  const segFragments = (applied ? applied.map(link => ({ tooth: link.tooth.value, url: `/api/mesh/${link.mesh_asset_id}` }))
    : draft ? draft.filter(item => state.segmentation.edits[item.mesh_asset_id]?.included)
      .map(item => ({ tooth: state.segmentation.edits[item.mesh_asset_id].tooth, url: item.url }))
    : (result.render_meshes || []).filter(item => item.source === "model-generated"))
    .filter(item => toothMatchesArch(item.tooth));
  if (scanLoaded && segFragments.length) {
    v.loadToothFragments(segFragments).then((loaded) => {
      if (v.fragmentError()) { state.scanRenderStatus = v.fragmentError(); renderScanStatus(); }
      if (loaded && (state.goalPreview?.evaluation || state.lastEval) === result) updateViewer(result);
    });
  } else {
    v.loadToothFragments([]);
    const renderMeshes = result.render_meshes?.length
      ? result.render_meshes
      : (state.useDemoMeshes ? demoRenderMeshes() : []);
    const filteredRenderMeshes = renderMeshes.filter((item) => toothMatchesArch(item.tooth));
    if (filteredRenderMeshes.length) {
      v.loadMeshes(filteredRenderMeshes).then((loaded) => {
        if (loaded && (state.goalPreview?.evaluation || state.lastEval) === result) updateViewer(result);
      });
    }
  }
  const visibleResult = filterResultForArch(result);
  // Uploaded scans can be picked only through their reviewed crown fragments.
  v.setSelectionEnabled(scanLoaded ? segFragments.length > 0 : scaleConfirmed(state.scanUnits));
  v.setSelectedTooth(state.manualEdit.selectedTooth);
  v.update({
    highlightTeeth: focusedTeeth(),
    frames: visibleResult.frames,
    toothFrames: visibleResult.tooth_frames,
    attachments: visibleResult.clinical_controls?.attachments || [],
    initialOffsets: state.demoInitialOffsets,
    stageIndex: Number(el("stageSlider").value || 0),
    view: state.view,
    exaggeration: state.userMode === "simple" ? 1 : (numberValue("exaggeration") || 1),
    showToothLabels: false, // Accessible number buttons surround the shared viewer.
    labelTeeth: state.userMode === "simple" ? [state.manualEdit.selectedTooth].filter(Boolean) : null,
    showScale: state.showScale,
    unitsConfirmed: scaleConfirmed(state.scanUnits),
    excluded: state.guided.excludedTeeth,
  });
  // The occlusal proximity overlay rides the registered scans. loadProximity caches
  // by map reference, so calling it every render is cheap when the map is unchanged.
  v.loadProximity(state.proximity.map);
  v.setProximityVisible(
    Boolean(state.scanArchFilter === "both" && state.proximity.enabled && state.proximity.map?.aligned_to_scan),
  );
  // Registered-bite view: move the lower arch into the estimated occlusal frame.
  // null for an as-scanned export (already occluding) or when the view is off.
  v.setArchRegistration(
    state.scanArchFilter === "both" && state.proximity.registeredView
      ? registeredOffsetForViewer(state.proximity.registration)
      : null,
  );
  // True-scale reference status (with the loaded scan's measured extent, if shown).
  const unitsConfirmed = scaleConfirmed(state.scanUnits);
  const extentMm = state.showScale && unitsConfirmed ? v.scanExtentMm() : null;
  state.scaleStatus = formatScaleStatus({
    enabled: state.showScale,
    hasScan: scanSources.length > 0,
    unitsConfirmed,
    extentMm,
  });
  renderScale();
}

export function renderAll() {
  document.body.dataset.mode = state.userMode;
  document.body.dataset.theme = state.theme;
  document.body.dataset.step = state.activeStep;
  document.body.dataset.sample = state.sample.active ? "1" : "";
  document.body.dataset.generationDetail = state.detailMode.generation;
  document.body.dataset.chatCollapsed = state.chat.collapsed ? "1" : "";
  el("themeToggle").setAttribute("aria-checked", state.theme === "dark" ? "true" : "false");
  const toothLabelBtn = el("toothLabelToggle");
  if (toothLabelBtn) {
    toothLabelBtn.setAttribute("aria-checked", String(state.showToothLabels));
    toothLabelBtn.classList.toggle("is-active", state.showToothLabels);
  }
  state.scanUnits = el("scanUnits").value;
  state.scanArch = el("scanArch").value;
  state.simpleGoal = el("simpleGoal").value;
  state.simpleAcknowledged = el("simpleAcknowledged").checked;
  state.generation.acknowledged = el("generationAck").checked;
  state.generation.notes = el("generationNotes").value;
  const segMissing = el("segmentMissingTeeth");
  if (segMissing) state.segmentation.missingTeeth = segMissing.value;
  state.versions.note = el("versionNote").value;
  state.caps = {
    linear_mm: numberValue("capLinear"),
    angular_deg: numberValue("capAngular"),
    rotation_deg: numberValue("capRotation"),
    intrusion_extrusion_mm: numberValue("capVertical"),
  };
  state.printExport = {
    enabled: el("printEnabled").checked,
    export_format: el("printFormat").value,
    delivery_email: el("printEmail").value,
    model_material: el("modelMaterial").value,
    thermoforming_material: el("thermoformingMaterial").value,
    safety_acknowledged: el("printSafety").checked,
    aligner_shell_enabled: el("alignerShellEnabled")?.checked || false,
    sheet_thickness_mm: numberValue("sheetThickness") || 0.6,
    gingival_trim_margin_mm: numberValue("trimMargin"),
  };
  state.clinicalControls = {
    fixedTeeth: el("fixedTeeth").value,
    attachmentTeeth: el("attachmentTeeth").value,
    movementExclusions: el("movementExclusions").value,
    iprContacts: state.clinicalControls.iprContacts,
  };
  renderSteps();
  // Relocates the shared viewer/AI/upload singletons into the active mode's
  // hosts and renders the guided wizard steps (no-op visuals when technician
  // view is active). Runs before updateViewer so the viewer is in its host
  // before it resizes.
  renderGuided();
  renderSampleComparison(renderAll);
  renderFocusTeeth(renderAll);
  renderReviewHeading();
  renderMetadata();
  renderUploadFileList();
  renderCaseRecordList();
  renderRows();
  renderIprContactMap();
  renderChat();
  renderGeneration();
  renderDetailModes();
  renderVersions();
  renderScanStatus();
  renderProximity();
  renderScale();
  renderCbctWorkflow();
  renderMovementFidelity();
  renderTrustStatus(el("trustStatusStrip"), state, renderAll);
  renderStagePlayback();
  renderSampleStatus();
  renderSegmentation();
  renderManualEdit();
  renderDirectControls();
  renderDownloadActions();
  const currentPlan = planJson();
  el("planJson").value = JSON.stringify(currentPlan, null, 2);
  updateStagePhase();
  scheduleEvaluate();
  renderSetupCompare();
  scheduleSetupCompare(currentPlan);
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
}

export function renderStagePreview() {
  updateStagePhase();
  el("stageSlider").max = String(Math.max(0, ((state.goalPreview?.evaluation || state.lastEval)?.frames?.length || 1) - 1));
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
}

function renderCbctWorkflow() {
  const workflow = state.cbctWorkflow || {};
  const status = el("cbctWorkflowStatus");
  if (!status) return;
  const mask = workflow.mask;
  const cbctRecords = state.caseRecords.filter((record) => record.kind === "cbct" || record.kind === "dicom");
  el("cbctRegistrationAccepted").checked = Boolean(workflow.registrationAccepted);
  el("cbctRegistrationRmse").value = workflow.rmseMm ?? 0.25;
  el("cbctRegistrationFitness").value = workflow.fitness ?? 0.9;
  el("proposeCbctAnatomy").disabled = Boolean(workflow.busy || !mask || !cbctRecords.length || !state.scanSources.length);
  const parts = [];
  if (!cbctRecords.length) parts.push("Attach a CBCT/DICOM record.");
  if (!state.scanSources.length) parts.push("Register a scan with the local engine.");
  if (!mask) parts.push("Import a root/bone mask JSON.");
  // The engine's fail-closed numeric gate on each registration's recorded
  // quality metrics: acceptance alone never unlocks CBCT-derived behavior.
  const gates = state.lastEval?.registration?.gate || [];
  const gateText = gates.length
    ? ` Registration quality gate: ${gates.map((g) => `${g.registration_id} ${g.verdict}`).join(", ")}.`
    : "";
  status.textContent = workflow.busy
    ? "Building proposed CBCT-derived anatomy..."
    : (workflow.status || parts.join(" ") || "Mask ready for proposal import.") + gateText;
}

function renderMovementFidelity() {
  const target = el("movementFidelityStatus");
  if (!target) return;
  const scanCount = state.scanSources.length || state.files.length;
  const appliedCount = state.segmentation.applied?.tooth_meshes?.length || 0;
  const renderLinks = state.lastEval?.render_meshes?.filter((item) => item.source === "model-generated") || [];
  if (appliedCount && renderLinks.length) {
    target.dataset.mode = "real";
    target.textContent = `Movement layer: reviewed per-tooth 3D meshes (${renderLinks.length}) moving over the scan.`;
  } else if (scanCount) {
    target.dataset.mode = "scan-only";
    target.textContent = "Individual selection and movement need reviewed tooth regions.";
  } else {
    target.dataset.mode = "schematic";
    target.textContent = "Movement layer: schematic preview until scans and reviewed per-tooth meshes are available.";
  }
}

function renderStagePlayback() {
  const button = el("stagePlayToggle");
  if (!button) return;
  const max = Number(el("stageSlider").max || 0);
  button.disabled = max <= 0;
  button.textContent = state.stagePlayback.playing ? "Pause" : "Play";
  button.setAttribute("aria-pressed", state.stagePlayback.playing ? "true" : "false");
  button.classList.toggle("is-active", state.stagePlayback.playing);
}

function renderReviewHeading() {
  el("reviewHeading").textContent = state.activeStep === "sample" ? "Sample Test Case" : "Progress Preview";
}

function filterScanSources(sources) {
  if (state.scanArchFilter === "both") return sources;
  return sources.filter((source) => (source.arch || inferArchFromName(source.name)) === state.scanArchFilter);
}

function toothMatchesArch(tooth) {
  if (state.scanArchFilter === "both") return true;
  const arch = archFromTooth(tooth);
  if (!arch) return true;
  return arch === state.scanArchFilter;
}

function filterResultForArch(result) {
  if (state.scanArchFilter === "both") return result;
  return {
    ...result,
    frames: (result.frames || []).map((frame) => ({
      ...frame,
      poses: (frame.poses || []).filter((pose) => toothMatchesArch(pose.tooth)),
    })),
    clinical_controls: {
      ...(result.clinical_controls || {}),
      attachments: (result.clinical_controls?.attachments || [])
        .filter((item) => toothMatchesArch(item.tooth?.value)),
    },
  };
}

export function renderGeneration() {
  const gen = state.generation;
  el("generationAck").checked = gen.acknowledged;
  el("generationNotes").value = gen.notes;
  el("generatePlan").disabled = gen.busy;
  el("generationStatus").textContent = gen.busy ? "Working..." : (gen.status || "Idle");
  el("generationConnector").textContent = generationConnectorHint();
  if (gen.landmarksStatus) el("landmarksStatus").textContent = gen.landmarksStatus;
  el("generationReport").innerHTML = gen.result ? generationReportMarkup(gen.result) : "";
}

function renderDetailModes() {
  document.querySelectorAll("[data-detail-mode]").forEach((button) => {
    const group = button.dataset.detailMode;
    button.classList.toggle("is-active", state.detailMode[group] === button.dataset.detailValue);
  });
}

// Tells the user exactly where the optional AI review gets its model/key, and
// whether it is currently wired up. Notes only feed that review step.
function generationConnectorHint() {
  if (state.chat.provider === "local") {
    return "AI review: local helper, offline. External review uses the Plan AI connector settings.";
  }
  const key = state.chat.apiKeyPresent ? "key in session" : "no key yet";
  const consent = state.chat.agentAccessEnabled ? "sharing acknowledged" : "sharing OFF — review will be skipped";
  return `AI review: ${state.chat.provider} · ${key} · ${consent}. Notes are sent only when sharing is on.`;
}

function generationReportMarkup(result) {
  const verdict = result.correctness?.verdict || "N/A";
  const ack = result.requires_acknowledgement
    ? "<p class=\"finding-gap\">This educational plan is not derived from your scan. Tick the acknowledgement and regenerate to confirm you understand.</p>"
    : "";
  const warnings = (result.warnings || [])
    .map((w) => `<li class="warning">${escapeHtml(w)}</li>`).join("");
  const steps = (result.steps || [])
    .map((s) => `<li class="${escapeHtml(s.status)}"><strong>${escapeHtml(s.name)}</strong>: ${escapeHtml(s.detail)}</li>`)
    .join("");
  const checks = (result.checks || [])
    .map((c) => `<li class="${c.passed ? "ok" : (c.severity === "gate" ? "warning" : "skipped")}">${c.passed ? "✓" : "✗"} <strong>${escapeHtml(c.name)}</strong>: ${escapeHtml(c.detail)}</li>`)
    .join("");
  const det = (result.deterministic_findings || []).length;
  const adv = (result.advisory_findings || []).length;
  const blocked = result.correctness?.fixed_teeth_moved?.length
    ? `<p class="finding-gap">Fixed teeth reported moved: ${escapeHtml(result.correctness.fixed_teeth_moved.join(", "))}</p>`
    : "";
  return `
    <p><strong>Source:</strong> ${escapeHtml(result.source)} · <strong>Correctness:</strong> ${escapeHtml(verdict)}</p>
    ${ack}
    <p>${result.stage_count} stage(s) · ${det} deterministic finding(s) · ${adv} linted advisory finding(s) · ${Number(result.correctness?.collision_count || 0)} crown overlap(s)</p>
    ${blocked}
    ${warnings ? `<ul>${warnings}</ul>` : ""}
    ${checks ? `<details open><summary>Correctness checks</summary><ul class="gen-steps">${checks}</ul></details>` : ""}
    <details><summary>Orchestration steps</summary><ul class="gen-steps">${steps}</ul></details>
    <p class="viewer-caveat">${escapeHtml(result.caveat || "")}</p>
  `;
}

export function renderVersions() {
  const v = state.versions;
  el("versionNote").value = v.note;
  el("saveVersion").disabled = v.busy;
  el("versionStatus").textContent = v.busy ? "Saving..." : v.status;
  el("versionList").innerHTML = v.list.length
    ? v.list.map((item, index) => `
        <li>
          <div>
            <strong>${escapeHtml(item.version_id)}</strong>
            <small>${escapeHtml((item.created_at || "").slice(0, 19).replace("T", " "))}</small>
            ${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}
            <code>${escapeHtml((item.plan_hash || "").slice(0, 12))}</code>
          </div>
          <button data-restore-version="${index}" type="button">Restore</button>
        </li>`).join("")
    : "<li class=\"chat-empty\">No saved versions yet.</li>";
}

const scheduleEvaluate = createEvaluationRunner({
  cacheKey: JSON.stringify,
  getPayload: planJson,
  evaluate: evaluatePlan,
  onPending: () => renderTrustStatus(el("trustStatusStrip"), state, renderAll, true),
  onResult(result) {
    state.engineError = null;
    if (result.ok === false) {
      state.lastEval = null;
      renderEngineErrors(result.errors || ["plan was rejected by the engine"]);
    } else {
      state.lastEval = result;
      renderGuided();
      renderEvaluation(result);
    }
    renderTrustStatus(el("trustStatusStrip"), state, renderAll);
  },
  onError(error) {
    state.lastEval = null;
    state.engineError = error.message;
    renderGuided();
    renderEngineOffline();
    renderTrustStatus(el("trustStatusStrip"), state, renderAll);
  },
});

export function renderAvailability() {
  el("availabilityGrid").innerHTML = Object.entries(availabilityLabels).map(([key, label]) => `
    <label class="toggle">
      <span>${escapeHtml(label)}</span>
      <input type="checkbox" data-availability="${key}" ${state.availability[key] ? "checked" : ""} />
    </label>
  `).join("");
}

function renderSteps() {
  document.querySelectorAll(".mode-choice").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.userMode === state.userMode);
  });
  document.querySelectorAll(".step").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.step === state.activeStep);
  });
  // Keep the Current/Planned/Overlay toolbar in sync with state.view. Without
  // this, programmatic view changes (e.g. the sample sets "overlay") leave the
  // toolbar showing "Current" - the static baseline view where the stage slider
  // moves nothing - so the preview looks frozen when scrubbing stages.
  document.querySelectorAll(".mode").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === state.view);
  });
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("is-active"));
  // Guided mode shows the #guided wizard (CSS-gated by body[data-mode]); the
  // technician panels stay inactive. In technician mode, activate the panel for
  // the current step (the sample step reuses the review panel).
  const panelId = state.activeStep === "sample" ? "panel-review" : `panel-${state.activeStep}`;
  el(panelId)?.classList.add("is-active");
}

function renderUploadFileList() {
  const statusNote = state.uploadStorageStatus ? `<p>${escapeHtml(state.uploadStorageStatus)}</p>` : "";
  let markup;
  if (state.files.length) {
    markup = `
      <div class="upload-file-heading">
        <strong>${state.files.length === 1 ? "Uploaded scan" : "Uploaded scans"}</strong>
        <button data-clear-uploads="true" type="button">Clear All</button>
      </div>
      ${statusNote}
      <ul>
        ${state.files.map((file, index) => `
          <li>
            <span>${escapeHtml(file.name)}</span>
            <small>${escapeHtml(uploadFileDetail(file))}</small>
            <button data-remove-upload="${index}" type="button" aria-label="Remove ${escapeHtml(file.name)}">x</button>
          </li>
        `).join("")}
      </ul>
    `;
  } else if (state.scanSources.length) {
    // The Sample Test Case loads its two scans as already-present records, so
    // step 1 shows them as "loaded" (read-only - they are not user uploads).
    markup = `
      <div class="upload-file-heading">
        <strong>Loaded scans</strong>
      </div>
      <ul>
        ${state.scanSources.map((source) => `
          <li>
            <span>${escapeHtml(source.name)}</span>
            <small>${escapeHtml(source.arch || "arch unknown")}</small>
          </li>
        `).join("")}
      </ul>
    `;
  } else {
    markup = `${statusNote}<p>No scan files are stored yet. Select upper, lower, or both arches.</p>`;
  }
  el("uploadFileList").innerHTML = markup;
  el("simpleUploadFileList").innerHTML = markup;
}

function uploadFileDetail(file) {
  const registered = state.scanSources.find((source) => source.name === file.name);
  const size = `${Math.round(file.size / 1024)} KB`;
  if (!registered?.asset) return size;
  const arch = registered.arch || "arch unknown";
  return `${size} · engine asset ${registered.asset.id} · ${arch}`;
}

function renderRows() {
  el("stageRows").innerHTML = state.rows.map((row, index) => `
    <tr>
      <td><input data-row="${index}" data-field="stage" type="number" min="0" value="${escapeHtml(row.stage)}" /></td>
      <td><input data-row="${index}" data-field="tooth" value="${escapeHtml(row.tooth)}" maxlength="2" /></td>
      <td><input data-row="${index}" data-field="x" type="number" step="0.01" value="${row.x}" /></td>
      <td><input data-row="${index}" data-field="y" type="number" step="0.01" value="${row.y}" /></td>
      <td><input data-row="${index}" data-field="z" type="number" step="0.01" value="${row.z}" /></td>
      <td><input data-row="${index}" data-field="tip" type="number" step="0.1" value="${row.tip}" /></td>
      <td><input data-row="${index}" data-field="torque" type="number" step="0.1" value="${row.torque}" /></td>
      <td><input data-row="${index}" data-field="rotation" type="number" step="0.1" value="${row.rotation}" /></td>
      <td><button class="remove-row" data-remove="${index}" type="button">×</button></td>
    </tr>
  `).join("");
}

function renderMetadata() {
  const sources = state.files.length ? state.files : state.scanSources;
  const totalSize = state.files.reduce((sum, file) => sum + file.size, 0);
  const items = state.files.length ? [
    ["Files", state.files.map((file) => file.name).join(", ")],
    ["Size", `${Math.round(totalSize / 1024)} KB`],
    ["Units", state.scanUnits],
    ["Arch", state.scanArch || "unknown"],
    ["Context records", String(state.caseRecords.length)],
  ] : sources.length ? [
    ["Files", sources.map((source) => source.name).join(", ")],
    ["Size", "repo example"],
    ["Units", state.scanUnits],
    ["Arch", "upper + lower"],
    ["Context records", String(state.caseRecords.length)],
  ] : [["Files", "none"], ["Size", "0 KB"], ["Units", state.scanUnits], ["Arch", "unknown"], ["Context records", String(state.caseRecords.length)]];
  el("scanMetadata").innerHTML = items
    .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("");
}

function renderCaseRecordList() {
  const container = el("caseRecordList");
  if (!container) return;
  const records = state.caseRecords;
  if (!records.length) {
    container.innerHTML = state.recordUploadStatus
      ? `<p>${escapeHtml(state.recordUploadStatus)}</p>`
      : "<p>No enhanced-review records attached.</p>";
    return;
  }
  container.innerHTML = `
    <div class="upload-file-heading">
      <strong>${records.length === 1 ? "Attached record" : "Attached records"}</strong>
    </div>
    ${state.recordUploadStatus ? `<p>${escapeHtml(state.recordUploadStatus)}</p>` : ""}
    <ul>
      ${records.map((record) => `
        <li>
          <span>${escapeHtml(record.filename || record.id)}</span>
          <small>${escapeHtml(caseRecordDetail(record))}</small>
          <button data-remove-record="${escapeHtml(record.id)}" type="button" aria-label="Remove ${escapeHtml(record.filename || record.id)}">x</button>
        </li>
      `).join("")}
    </ul>
  `;
}

function caseRecordDetail(record) {
  const bits = [record.kind];
  if (record.modality) bits.push(record.modality);
  if (record.size_bytes != null) bits.push(`${Math.round(record.size_bytes / 1024)} KB`);
  if (record.local_reference) bits.push("local reference");
  return bits.join(" · ");
}

function renderEvaluation(result) {
  result = state.goalPreview?.evaluation || result;
  renderReviewTier(result.review_tier);
  renderCbct(result.cbct_status, result.cbct_handoff, result.registration);
  renderAnatomyReview(result.derived_anatomy);
  el("dataGapList").innerHTML = dataGapMarkup(result);
  renderAcquisitionAdvice(result.acquisition_advice);

  el("findingList").innerHTML = result.findings.length
    ? result.findings.map(findingMarkup).join("")
    : "<li>No deterministic findings</li>";

  const t = result.timeline;
  el("timelineText").textContent =
    `${t.stage_count} stage(s), ${t.projected_duration_days} projected day(s) ` +
    `(~${t.projected_duration_weeks} weeks) at ${t.wear_interval_days}-day wear. ${t.caveat}`;

  const slider = el("stageSlider");
  const lastStage = Math.max(0, result.frames.length - 1);
  slider.max = String(lastStage);
  if (Number(slider.value) > lastStage) slider.value = String(lastStage);
  updateStagePhase(result);
  drawCanvas();
  updateViewer(result);
  if (pendingRefit) {
    pendingRefit = false;
    ensureViewer()?.recenter();
  }
  renderPrintExport(el("printExportStatus"), result.print_export);
  renderOptimizedStaging(result.optimized_staging);
  renderDownloadActions();
}

function renderReviewTier(info) {
  const container = el("reviewTierBanner");
  if (!container) return;
  if (!info) {
    container.innerHTML = "";
    return;
  }
  const expanded = container.querySelector("details")?.open;
  container.dataset.tier = info.tier;
  container.innerHTML = `
    <p class="review-tier-label"><strong>${escapeHtml(info.label)}</strong></p>
    <details class="review-scope-details" ${expanded ? "open" : ""}><summary>Scope & limitations</summary>
    <p class="review-tier-summary">${escapeHtml(info.summary)}</p>
    ${info.root_bone_aware
      ? ""
      : `<p class="review-tier-note">Root/bone-aware review is not available for this plan.</p>`}
    </details>
  `;
}

const CBCT_STATUS_COPY = {
  unavailable: "No CBCT/DICOM volume is attached.",
  attached: "CBCT/DICOM attached for reference only. Not registered; root/bone checks stay unavailable.",
  viewed: "CBCT opened in a local viewer. Still not registered to the scan.",
  registered: "CBCT registered to the surface scan. Anatomy review still pending.",
  "anatomy-reviewed": "CBCT registered and root/bone anatomy reviewed.",
};

function renderCbct(status, handoff, registration) {
  const panel = el("cbctPanel");
  const banner = el("cbctBanner");
  if (!panel || !banner) return;
  if (!status || status === "unavailable") {
    panel.hidden = true;
    banner.innerHTML = "";
    return;
  }
  panel.hidden = false;
  banner.dataset.tier = status === "anatomy-reviewed" ? "root-bone-aware" : "cbct-attached";
  const refs = handoff?.local_references || [];
  banner.innerHTML = `
    <p class="review-tier-label"><strong>CBCT status: ${escapeHtml(status)}</strong></p>
    <p class="review-tier-summary">${escapeHtml(CBCT_STATUS_COPY[status] || "")}</p>
    ${handoff?.available ? `
      <p class="review-tier-summary">${escapeHtml(handoff.instructions)}</p>
      <p class="review-tier-note">Suggested viewer: ${escapeHtml(handoff.viewer_suggestion)}</p>
      ${refs.length ? `<ul>${refs.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : ""}
    ` : ""}
    ${registrationMarkup(registration)}
  `;
}

function registrationMarkup(registration) {
  const transforms = registration?.transforms || [];
  if (!transforms.length) return "";
  const rows = transforms.map((t) => {
    const q = t.quality;
    const metrics = q
      ? [
          q.rmse_mm != null ? `RMSE ${Number(q.rmse_mm).toFixed(3)} mm` : null,
          q.fitness != null ? `fitness ${Number(q.fitness).toFixed(2)}` : null,
          q.inlier_ratio != null ? `inliers ${Number(q.inlier_ratio).toFixed(2)}` : null,
        ].filter(Boolean).join(" · ")
      : "no quality metrics";
    const state = t.accepted ? (q ? "accepted" : "accepted (no quality - not usable)") : "proposed";
    return `<li><strong>${escapeHtml(t.method)}</strong> · ${escapeHtml(state)} · ${escapeHtml(metrics)}</li>`;
  }).join("");
  return `
    <p class="review-tier-note">Registration${registration.ready ? " (accepted, quality-backed)" : " (not yet usable)"}:</p>
    <ul>${rows}</ul>
  `;
}

function dataGapMarkup(result) {
  if (Array.isArray(result.data_gap_actions) && result.data_gap_actions.length) {
    return result.data_gap_actions.map((action) => `
      <li>
        <strong>${escapeHtml(action.gap)}</strong>
        <p>${escapeHtml(action.impact)}</p>
        <p>${escapeHtml(action.next_step)}</p>
      </li>
    `).join("");
  }
  return result.data_gaps.map((gap) => `<li>${escapeHtml(gap)}</li>`).join("");
}

function renderAcquisitionAdvice(advice) {
  if (!advice) {
    el("acquisitionCaveat").textContent = "";
    el("acquisitionList").innerHTML = "";
    return;
  }
  el("acquisitionCaveat").textContent = advice.caveat || "";
  const impacts = Array.isArray(advice.impacts) ? advice.impacts.slice(0, 4) : [];
  el("acquisitionList").innerHTML = impacts.length
    ? impacts.map(acquisitionMarkup).join("")
    : "<li>No missing data modalities are currently applicable.</li>";
}

function acquisitionMarkup(impact) {
  const closed = impact.closes_data_gaps?.length
    ? `<p>Closes: ${escapeHtml(impact.closes_data_gaps.join(", "))}</p>`
    : "";
  const resolves = impact.resolves?.length
    ? `<p>Clears: ${escapeHtml(impact.resolves.map((finding) => finding.title).join("; "))}</p>`
    : "";
  const surfaces = impact.surfaces?.length
    ? `<p>Unlocks: ${escapeHtml(impact.surfaces.map((finding) => finding.title).join("; "))}</p>`
    : "";
  return `<li>
    <strong>${escapeHtml(impact.label)} (${Number(impact.priority_score || 0).toFixed(1)})</strong>
    <p>${escapeHtml(impact.acquisition)}</p>
    ${closed}${resolves}${surfaces}
    <p>${escapeHtml(impact.note)}</p>
  </li>`;
}

function findingMarkup(finding) {
  const question = finding.clinician_question
    ? `<p class="finding-question">${escapeHtml(finding.clinician_question)}</p>`
    : "";
  const gap = finding.data_gap ? `<p class="finding-gap">${escapeHtml(finding.data_gap)}</p>` : "";
  return `<li class="${escapeHtml(finding.severity)}">
    <strong>${escapeHtml(finding.title)}</strong>
    <p>${escapeHtml(finding.message)}</p>${gap}${question}
  </li>`;
}

function renderEngineErrors(errors) {
  el("findingList").innerHTML = errors
    .map((message) => `<li class="warning"><strong>Plan rejected</strong><p>${escapeHtml(message)}</p></li>`)
    .join("");
  el("timelineText").textContent = "Plan invalid - fix the errors above to re-evaluate.";
  updateStagePhase(null);
  el("printExportStatus").innerHTML = "";
  renderDownloadActions();
}

function renderEngineOffline() {
  el("findingList").innerHTML =
    "<li class=\"warning\"><strong>Evaluation engine offline</strong>" +
    "<p>Start it with <code>python -m orthoplan.server</code> (or <code>orthoplan serve</code>) " +
    "and open this page from that server. Findings are computed by the Python engine only.</p></li>";
  el("dataGapList").innerHTML = "";
  el("acquisitionCaveat").textContent = "";
  el("acquisitionList").innerHTML = "";
  el("printExportStatus").innerHTML = "";
  el("optimizedStaging").innerHTML = "";
  el("timelineText").textContent = "Engine offline - no projection available.";
  updateStagePhase(null);
  renderDownloadActions();
}

function renderScanStatus() {
  el("scanRenderStatus").textContent = state.scanRenderStatus;
  el("scanArchFilter").value = state.scanArchFilter;
}

function renderProximity() {
  const button = el("proximityToggle");
  if (!button) return;
  const prox = state.proximity;
  const active = Boolean(prox.enabled && prox.map?.aligned_to_scan);
  button.classList.toggle("is-active", active);
  button.setAttribute("aria-pressed", active ? "true" : "false");
  button.disabled = prox.busy;
  button.textContent = prox.busy ? "Bite…" : "Bite proximity";
  const legend = el("proximityLegend");
  if (legend) legend.hidden = !active;
  const status = el("proximityStatus");
  if (status) {
    status.textContent = prox.status;
    status.hidden = !prox.status;
  }
  const regButton = el("registeredBiteToggle");
  if (regButton) {
    regButton.classList.toggle("is-active", Boolean(prox.registeredView));
    regButton.setAttribute("aria-pressed", prox.registeredView ? "true" : "false");
    regButton.disabled = prox.busy;
  }
}

function renderScale() {
  const button = el("scaleToggle");
  if (button) {
    button.classList.toggle("is-active", state.showScale);
    button.setAttribute("aria-pressed", state.showScale ? "true" : "false");
  }
  const status = el("scaleStatus");
  if (status) {
    status.textContent = state.scaleStatus;
    status.hidden = !state.scaleStatus;
  }
}

function renderSampleStatus() {
  const chip = el("sampleStatusChip");
  chip.hidden = !state.sampleStatus;
  chip.textContent = state.sampleStatus;
  // The sidebar launcher doubles as the exit so the sample is always escapable,
  // in either Guided or Technician view, as the user navigates.
  const launch = el("sampleLaunch");
  if (launch) {
    launch.textContent = state.sample.active ? "Exit Sample Test Case" : "Sample Test Case";
    launch.classList.toggle("is-active-sample", state.sample.active);
  }
}

// Manual target authoring panel. The user clicks a tooth in the 3D preview and
// nudges its final IN-PLANE position; the authored target is a normal manual
// stage delta in state.rows, so Generate Plan re-stages it into cap-respecting
// stages. Authoring is gated on confirmed scan units (mm) - the engine treats
// other units as unverified, so a mm nudge would be meaningless.
function renderManualEdit() {
  const panel = el("manualEdit");
  if (!panel) return; // panel not present (e.g. trimmed markup)
  const confirmed = scaleConfirmed(state.scanUnits);
  const selected = state.manualEdit.selectedTooth;
  panel.dataset.scaleConfirmed = confirmed ? "1" : "";
  panel.dataset.selected = selected ? "1" : "";

  const gate = el("manualEditGate");
  if (gate) {
    gate.textContent = confirmed
      ? "Click a tooth in the preview, then nudge its final position. Generate Plan splits the target into cap-respecting stages."
      : "Confirm the scan units (set Units to mm) before authoring a target - millimetre nudges are meaningless while units are unverified.";
  }

  const selectionLabel = el("manualEditSelection");
  if (selectionLabel) {
    selectionLabel.textContent = selected ? `Selected tooth: ${selected}` : "No tooth selected.";
  }

  const readout = el("manualEditReadout");
  if (readout) {
    if (selected) {
      const t = targetFor(state.rows, selected);
      readout.textContent =
        `Target (geometric, crown translation only): x ${t.x.toFixed(2)} mm, y ${t.y.toFixed(2)} mm ` +
        `(${targetMagnitudeMm(t).toFixed(2)} mm in-plane). Not a treatment goal or approval.`;
    } else {
      readout.textContent = "";
    }
  }

  const editable = confirmed && Boolean(selected);
  for (const id of ["manualNudgeXMinus", "manualNudgeXPlus", "manualNudgeYMinus", "manualNudgeYPlus", "manualTargetReset"]) {
    const btn = el(id);
    if (btn) btn.disabled = !editable;
  }
  const clearBtn = el("manualClearSelection");
  if (clearBtn) clearBtn.disabled = !selected;
}

function renderDirectControls() {
  const panel = el("directControls");
  if (!panel) return;
  const selected = state.manualEdit.selectedTooth;
  const appliedSegmentation = Boolean(state.segmentation.applied?.tooth_meshes?.length);
  const gate = controlGate({
    unitsConfirmed: scaleConfirmed(state.scanUnits),
    segmentedTeeth: appliedSegmentation,
    rootsAvailable: Boolean(state.availability.roots || state.derivedAnatomy?.roots?.length),
    reviewedAnatomy: state.lastEval?.review_tier?.root_bone_aware,
  });
  const familyHost = el("directControlFamilies");
  if (familyHost) {
    familyHost.innerHTML = Object.keys(CONTROL_AXES).map((family) => `
      <button data-direct-family="${escapeHtml(family)}" class="${state.directControls.selectedFamily === family ? "is-active" : ""}" type="button">
        ${escapeHtml(family.replace(/_/g, " "))}
      </button>
    `).join("");
  }
  const status = el("directControlStatus");
  if (status) {
    status.textContent = selected
      ? `Selected tooth ${selected}`
      : "Select a tooth in the 3D preview";
  }
  const axes = CONTROL_AXES[state.directControls.selectedFamily] || [];
  const editable = Boolean(selected && gate.allowed);
  const grid = el("directControlGrid");
  if (grid) {
    grid.innerHTML = axes.map((axis) => {
      const step = CONTROL_STEPS[axis] || 0.1;
      const unit = axis === "x" || axis === "y" || axis === "z" ? "mm" : "deg";
      return `
        <div class="direct-axis">
          <span>${escapeHtml(axisLabel(axis))}</span>
          <button data-direct-axis="${escapeHtml(axis)}" data-direct-delta="${-step}" ${editable ? "" : "disabled"} type="button">-</button>
          <button data-direct-axis="${escapeHtml(axis)}" data-direct-delta="${step}" ${editable ? "" : "disabled"} type="button">+</button>
          <small>${escapeHtml(step)} ${unit}</small>
        </div>
      `;
    }).join("");
  }
  const archAmount = el("archResponseAmount");
  if (archAmount) archAmount.value = state.directControls.archResponseMm;
  const archButton = el("applyArchResponse");
  if (archButton) archButton.disabled = !editable;
  const warnings = [
    ...gate.blockers,
    ...gate.warnings,
    ...(state.directControls.warnings || []),
  ];
  const warningTarget = el("directControlWarnings");
  if (warningTarget) {
    warningTarget.textContent = warnings.length
      ? warnings.join(". ")
      : "Direct controls are geometric proposals and remain review-gated; generate/restage and review findings before use.";
  }
}

function axisLabel(axis) {
  return {
    x: "Translate X",
    y: "Translate Y",
    z: "Intrude / extrude",
    tip: "Crown tip",
    torque: "Crown torque",
    rotation: "Rotation",
  }[axis] || axis;
}

function renderDownloadActions() {
  el("downloadEvaluation").disabled = !state.lastEval;
  el("downloadPrintMetadata").disabled = !state.lastEval?.print_export;
  renderMovementReadiness();
}

function renderMovementReadiness() {
  const target = el("movementReadinessChecklist");
  if (!target) return;
  const scanReady = Boolean(state.scanSources.length || state.files.length);
  const unitsReady = scaleConfirmed(state.scanUnits);
  const appliedMeshes = state.segmentation.applied?.tooth_meshes?.length || 0;
  const renderMeshes = state.lastEval?.render_meshes?.filter((item) => item.source === "model-generated").length || 0;
  const printReady = Boolean(state.lastEval?.print_export?.ready);
  const items = [
    ["Scan registered", scanReady],
    ["Units confirmed in mm", unitsReady],
    ["Reviewed per-tooth meshes applied", appliedMeshes > 0],
    ["3D movement uses real tooth fragments", renderMeshes > 0],
    ["Print package inputs complete", printReady],
  ];
  target.innerHTML = `
    <strong>Real movement / print checklist</strong>
    <ul>
      ${items.map(([label, ok]) => `<li data-ok="${ok ? "1" : "0"}">${ok ? "✓" : "○"} ${escapeHtml(label)}</li>`).join("")}
    </ul>
  `;
}

function renderOptimizedStaging(status) {
  if (!status) {
    el("optimizedStaging").innerHTML = "";
    return;
  }
  const issues = status.issues?.length
    ? `<ul>${status.issues.map((issue) => `<li>${escapeHtml(issue.tooth)}: ${escapeHtml(issue.message)}</li>`).join("")}</ul>`
    : "<p>No fixed-tooth or movement-exclusion conflicts in the optimizer input.</p>";
  el("optimizedStaging").innerHTML = `
    <p><strong>${Number(status.stage_count || 0)} suggested stage(s)</strong></p>
    ${issues}
    <p>${escapeHtml(status.caveat)}</p>
  `;
}

function renderIprContactMap() {
  el("iprContactMap").innerHTML = iprContactPairs.map(([a, b]) => {
    const key = `${a}-${b}`;
    const value = state.clinicalControls.iprContacts[key] || "";
    return `
      <label class="ipr-contact">
        <span>${escapeHtml(a)}-${escapeHtml(b)}</span>
        <input data-ipr-contact="${escapeHtml(key)}" type="number" min="0" step="0.05" value="${escapeHtml(value)}" />
      </label>
    `;
  }).join("");
}

function drawCanvas() {
  const canvas = el("archCanvas");
  const ctx = canvas.getContext("2d");
  const styles = getComputedStyle(document.body);
  const canvasColor = styles.getPropertyValue("--canvas").trim() || "#fbfdfe";
  const lineColor = styles.getPropertyValue("--line").trim() || "#cdd6dc";
  const mutedColor = styles.getPropertyValue("--muted").trim() || "#60707a";
  const accentColor = styles.getPropertyValue("--accent").trim() || "#0f766e";
  const blueColor = styles.getPropertyValue("--blue").trim() || "#2563eb";
  const stageIndex = Number(el("stageSlider").value || 0);
  const visibleResult = state.lastEval ? filterResultForArch(state.lastEval) : null;
  const totals = framePoseTotals(visibleResult?.frames?.[stageIndex]);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = canvasColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(520, 258, 410, 210, 0, 0, Math.PI * 2);
  ctx.stroke();

  for (const [tooth, [x, y]] of Object.entries(toothPositions)) {
    if (!toothMatchesArch(tooth)) continue;
    const movement = totals.get(tooth) || { x: 0, y: 0, z: 0 };
    const initial = state.demoInitialOffsets[tooth] || { x: 0, y: 0, z: 0 };
    const ix = initial.x * 80;
    const iy = initial.y * 80 - initial.z * 35;
    const dx = movement.x * 80;
    const dy = movement.y * 80 - movement.z * 35;
    if (state.view === "overlay" || state.view === "current") {
      drawTooth(ctx, x + ix, y + iy, tooth, lineColor, mutedColor, mutedColor);
    }
    if (state.view === "overlay" || state.view === "planned") {
      drawTooth(ctx, x + ix + dx, y + iy + dy, tooth, accentColor, "#ffffff", lineColor);
      if (Math.hypot(dx, dy) > 1) {
        ctx.strokeStyle = blueColor;
        ctx.beginPath();
        ctx.moveTo(x + ix, y + iy);
        ctx.lineTo(x + ix + dx, y + iy + dy);
        ctx.stroke();
      }
    }
  }
}

function drawTooth(ctx, x, y, label, fill, text, stroke) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  toothPath(ctx, x, y, label);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = text;
  ctx.font = "12px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, x, y);
}

function toothPath(ctx, x, y, label) {
  const kind = toothKind(label);
  if (kind === "molar") {
    ctx.moveTo(x - 20, y - 10);
    ctx.bezierCurveTo(x - 23, y - 20, x - 8, y - 23, x, y - 17);
    ctx.bezierCurveTo(x + 8, y - 23, x + 23, y - 20, x + 20, y - 10);
    ctx.bezierCurveTo(x + 26, y, x + 20, y + 19, x + 8, y + 18);
    ctx.bezierCurveTo(x, y + 24, x - 26, y + 18, x - 20, y - 10);
    return;
  }
  if (kind === "premolar") {
    ctx.moveTo(x - 18, y - 8);
    ctx.bezierCurveTo(x - 17, y - 20, x - 4, y - 22, x, y - 14);
    ctx.bezierCurveTo(x + 4, y - 22, x + 17, y - 20, x + 18, y - 8);
    ctx.bezierCurveTo(x + 20, y + 12, x + 8, y + 20, x, y + 16);
    ctx.bezierCurveTo(x - 8, y + 20, x - 20, y + 12, x - 18, y - 8);
    return;
  }
  if (kind === "canine") {
    ctx.moveTo(x - 16, y - 6);
    ctx.bezierCurveTo(x - 12, y - 20, x - 3, y - 22, x, y - 26);
    ctx.bezierCurveTo(x + 3, y - 22, x + 12, y - 20, x + 16, y - 6);
    ctx.bezierCurveTo(x + 18, y + 10, x + 8, y + 19, x, y + 17);
    ctx.bezierCurveTo(x - 8, y + 19, x - 18, y + 10, x - 16, y - 6);
    return;
  }
  ctx.moveTo(x - 16, y - 12);
  ctx.bezierCurveTo(x - 18, y - 22, x + 18, y - 22, x + 16, y - 12);
  ctx.lineTo(x + 13, y + 14);
  ctx.bezierCurveTo(x + 8, y + 22, x - 8, y + 22, x - 13, y + 14);
  ctx.closePath();
}
