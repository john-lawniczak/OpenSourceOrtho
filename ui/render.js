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
  confidenceTier,
  countNoteMarkup,
  createLatest,
  escapeHtml,
  framePoseTotals,
  inferArchFromName,
  toothKind,
} from "./core.js";
import { createViewer } from "./viewer3d.js";
import { planJson } from "./plan.js";
import { renderGuided, toggleExcludedTooth } from "./guided.js";
import { scaleConfirmed, targetFor, targetMagnitudeMm } from "./manual_edit.js";
import { parseMissingTeeth } from "./segment.js";
import { formatScaleStatus } from "./scale.js";
import { registeredOffsetForViewer } from "./proximity.js";

let viewer = null;
let viewerFailed = false;
let renderedChatCount = 0;
let renderedChatSignature = "";
// One-shot request to re-frame the camera once the next evaluation has populated
// the scene. Used when a new scene becomes visible (sample screen, guided 3D
// step) where the viewer may have been sized while hidden or framed for a
// different scene. It is honored after the async evaluation renders, so the fit
// uses the real container size and the new geometry.
let pendingRefit = false;

export function requestViewerRefit() {
  pendingRefit = true;
}

// The guided steps that show the 3D viewer for picking teeth (click a tooth to
// hold it still). Returns the step id, or null when not in that context.
function guidedSelectionStep() {
  if (state.userMode !== "simple") return null;
  const step = state.guided.step;
  return step === "plan" || step === "details" ? step : null;
}

function formatWeek(value) {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function updateStagePhase(result = state.lastEval) {
  const slider = el("stageSlider");
  const stageIndex = Number(slider.value || 0);
  el("stageValue").textContent = String(stageIndex);
  if (!result?.timeline) {
    el("stagePhase").textContent = "Aligner timeline unavailable";
    return;
  }
  const totalAligners = Math.max(1, Number(result.timeline.stage_count || result.frames?.length || 1));
  const alignerNumber = Math.min(totalAligners, stageIndex + 1);
  const wearDays = Math.max(0, Number(result.timeline.wear_interval_days || 0));
  const weekStart = (stageIndex * wearDays) / 7;
  const weekEnd = ((stageIndex + 1) * wearDays) / 7;
  el("stagePhase").textContent =
    `Aligner ${alignerNumber} of ${totalAligners} · Weeks ${formatWeek(weekStart)}-${formatWeek(weekEnd)}`;
}

function ensureViewer() {
  if (viewer || viewerFailed) return viewer;
  try {
    viewer = createViewer(el("viewer3d"));
    // Clicking a tooth means different things by context. In the guided "teeth"
    // and "details" steps it toggles whether that tooth is held still (the visual
    // equivalent of the checkbox list). Everywhere else it selects the tooth for
    // manual target authoring (only honored when scan units are confirmed).
    viewer.setSelectionHandler((tooth) => {
      if (guidedSelectionStep()) {
        toggleExcludedTooth(tooth);
      } else {
        state.manualEdit.selectedTooth = tooth;
      }
      renderAll();
    });
  } catch (error) {
    viewerFailed = true;
    el("viewer3d").hidden = true;
    el("viewerZoom").hidden = true;
    el("archCanvas").hidden = false;
    state.dim = "2d";
  }
  return viewer;
}

// Called by the 3D/2D toggle. Falls back to 2D if WebGL is unavailable.
export function setDimension(dim) {
  state.dim = dim;
  const use3d = dim === "3d" && !viewerFailed;
  el("viewer3d").hidden = !use3d;
  el("archCanvas").hidden = use3d;
  el("viewerZoom").hidden = !use3d;
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

function updateViewer(result) {
  if (state.dim !== "3d") return;
  const v = ensureViewer();
  if (!v) return;
  v.resize();
  const allScanSources = state.files.length
    ? state.files.map((file) => ({ name: file.name, file, arch: inferArchFromName(file.name) }))
    : state.scanSources;
  const scanSources = filterScanSources(allScanSources);
  if (scanSources.length) {
    v.loadScanSources(scanSources).then(({ loaded, count }) => {
      state.scanRenderStatus = count
        ? "Showing your scan. Tooth movement in the preview is simulated."
        : "Your scan could not be displayed.";
      renderScanStatus();
      if (loaded && state.lastEval === result) updateViewer(result);
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
  const segFragments = (result.render_meshes || [])
    .filter((item) => item.source === "model-generated" && toothMatchesArch(item.tooth));
  if (scanLoaded && segFragments.length) {
    v.loadToothFragments(segFragments).then((loaded) => {
      if (loaded && state.lastEval === result) updateViewer(result);
    });
  } else {
    const renderMeshes = result.render_meshes?.length
      ? result.render_meshes
      : (state.useDemoMeshes ? demoRenderMeshes() : []);
    const filteredRenderMeshes = renderMeshes.filter((item) => toothMatchesArch(item.tooth));
    if (filteredRenderMeshes.length) {
      v.loadMeshes(filteredRenderMeshes).then((loaded) => {
        if (loaded && state.lastEval === result) updateViewer(result);
      });
    }
  }
  const visibleResult = filterResultForArch(result);
  const guidedSelect = guidedSelectionStep();
  // Tooth picking is enabled for manual authoring once units are confirmed, and
  // unconditionally in the guided teeth/details steps (there a click just toggles
  // "hold still", which needs no millimetre scale).
  v.setSelectionEnabled(Boolean(guidedSelect) || scaleConfirmed(state.scanUnits));
  v.setSelectedTooth(state.manualEdit.selectedTooth);
  // In the guided teeth/details steps the viewer is a selection/`preview-scale`
  // aid, so show the planned movement at the last stage in overlay (the slider
  // and view toolbar are hidden there); elsewhere honor the live controls.
  const lastStage = Math.max(0, (visibleResult.frames?.length || 1) - 1);
  v.update({
    frames: visibleResult.frames,
    toothFrames: visibleResult.tooth_frames,
    attachments: visibleResult.clinical_controls?.attachments || [],
    initialOffsets: state.demoInitialOffsets,
    stageIndex: guidedSelect ? lastStage : Number(el("stageSlider").value || 0),
    view: guidedSelect ? "overlay" : state.view,
    exaggeration: numberValue("exaggeration") || 1,
    showToothLabels: guidedSelect === "plan" ? true : state.showToothLabels,
    showScale: state.showScale,
    unitsConfirmed: scaleConfirmed(state.scanUnits),
    excluded: state.guided.excludedTeeth,
  });
  // The occlusal proximity overlay rides the registered scans. loadProximity caches
  // by map reference, so calling it every render is cheap when the map is unchanged.
  v.loadProximity(state.proximity.map);
  v.setProximityVisible(
    Boolean(state.proximity.enabled && state.proximity.map?.aligned_to_scan),
  );
  // Registered-bite view: move the lower arch into the estimated occlusal frame.
  // null for an as-scanned export (already occluding) or when the view is off.
  v.setArchRegistration(
    state.proximity.registeredView ? registeredOffsetForViewer(state.proximity.registration) : null,
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
    toothLabelBtn.setAttribute("aria-pressed", state.showToothLabels ? "true" : "false");
    toothLabelBtn.classList.toggle("is-active", state.showToothLabels);
  }
  state.scanUnits = el("scanUnits").value;
  state.scanArch = el("scanArch").value;
  state.simpleGoal = el("simpleGoal").value;
  state.simpleAcknowledged = el("simpleAcknowledged").checked;
  state.chat.provider = el("chatProvider").value || state.chat.provider;
  state.chat.model = currentChatModel();
  state.chat.input = el("chatInput").value;
  state.chat.apiKeyPresent = Boolean(el("chatApiKey").value.trim());
  state.chat.agentAccessEnabled = el("agentAccessEnabled").checked;
  state.chat.agentEndpoint = el("agentEndpoint").value;
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
  renderSampleStatus();
  renderSegmentation();
  renderManualEdit();
  renderDownloadActions();
  el("planJson").value = JSON.stringify(planJson(), null, 2);
  updateStagePhase();
  scheduleEvaluate();
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
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

const AI_KEY_HELP = {
  local: "The local helper runs on this machine and needs no API key.",
  openai: "Paste your OpenAI API key (from platform.openai.com). It is used only for this session and never saved.",
  "claude-code": "Paste your Anthropic API key (from console.anthropic.com). It is used only for this session and never saved.",
  mcp: "Paste the API key your MCP host expects (set the endpoint under Connector settings). Used only for this session.",
  "open-source": "Set the model endpoint under Connector settings. Paste a key only if your endpoint requires one; used only for this session.",
};

export function renderChat() {
  renderChatConnectorControls();
  el("chatInput").value = state.chat.input;
  el("agentAccessEnabled").checked = state.chat.agentAccessEnabled;
  el("agentEndpoint").value = state.chat.agentEndpoint;
  el("sendChat").disabled = state.chat.busy || !state.chat.input.trim();
  const toggle = el("toggleChatPanel");
  if (toggle) {
    toggle.textContent = state.chat.collapsed ? "Show" : "Hide";
    toggle.setAttribute("aria-expanded", state.chat.collapsed ? "false" : "true");
    toggle.setAttribute("aria-label", state.chat.collapsed ? "Expand AI chat" : "Collapse AI chat");
  }
  // The reopen tab is the only visible handle once the panel slides off-screen.
  const reopenTab = el("chatReopenTab");
  if (reopenTab) reopenTab.hidden = !state.chat.collapsed;
  const contextEl = el("chatStageContext");
  if (contextEl) contextEl.textContent = chatStageLabel();
  // The local helper needs no key, so hide the key field for it; for any real
  // provider show the field with provider-specific, plain-language instructions.
  const isLocal = state.chat.provider === "local";
  const connector = chatConnector(state.chat.provider);
  el("aiKeyField").hidden = isLocal || connector?.requires_api_key === false;
  el("chatCustomModelField").hidden = !connector?.allow_custom_model;
  el("aiKeyHelp").textContent = AI_KEY_HELP[state.chat.provider] || AI_KEY_HELP.local;
  const secretStatus = state.chat.apiKeyPresent ? " · key in session" : "";
  const agentStatus = state.chat.agentAccessEnabled ? " · agent access staged" : "";
  el("chatStatus").textContent = `${state.chat.status}${secretStatus}${agentStatus}`;
  renderChatMessages();
}

function currentChatModel() {
  const custom = el("chatCustomModel")?.value.trim();
  const selected = el("chatModel")?.value;
  if (selected === "__custom__") return custom || state.chat.model || "custom-model";
  return selected || state.chat.model;
}

function chatConnector(kind) {
  return (state.chat.connectors || []).find((connector) => connector.kind === kind);
}

function renderChatConnectorControls() {
  const provider = el("chatProvider");
  const model = el("chatModel");
  const custom = el("chatCustomModel");
  const connectors = state.chat.connectors || [];
  const providerSignature = connectors.map((item) => `${item.kind}:${item.label}`).join("|");
  if (provider.dataset.signature !== providerSignature) {
    provider.replaceChildren(...connectors.map((connector) => {
      const option = document.createElement("option");
      option.value = connector.kind;
      option.textContent = connector.shares_patient_data
        ? `${connector.label} (shares plan context)`
        : connector.label;
      return option;
    }));
    provider.dataset.signature = providerSignature;
  }
  provider.value = state.chat.provider;
  const connector = chatConnector(state.chat.provider) || connectors[0];
  const models = connector?.models?.length ? connector.models : [connector?.model || state.chat.model];
  const modelSignature = `${connector?.kind || ""}:${models.join("|")}:${connector?.allow_custom_model ? "custom" : ""}`;
  if (model.dataset.signature !== modelSignature) {
    const options = models.map((modelId) => {
      const option = document.createElement("option");
      option.value = modelId;
      option.textContent = modelId;
      return option;
    });
    if (connector?.allow_custom_model) {
      const option = document.createElement("option");
      option.value = "__custom__";
      option.textContent = "Custom model ID";
      options.push(option);
    }
    model.replaceChildren(...options);
    model.dataset.signature = modelSignature;
  }
  const selected = state.chat.modelByProvider[state.chat.provider] || connector?.model || models[0];
  const customSelected = connector?.allow_custom_model && !models.includes(selected);
  model.value = customSelected ? "__custom__" : selected;
  custom.value = customSelected ? selected : custom.value;
  state.chat.model = customSelected ? custom.value : model.value;
}

function renderChatMessages() {
  const host = el("chatMessages");
  const signature = state.chat.messages.map((message) => `${message.role}:${message.content}`).join("\n");
  if (!state.chat.messages.length) {
    if (renderedChatSignature !== signature) {
      host.replaceChildren(chatEmptyNode("Ask what the preview can and cannot tell you."));
      renderedChatCount = 0;
      renderedChatSignature = signature;
    }
    return;
  }
  if (!signature.startsWith(renderedChatSignature) || renderedChatCount > state.chat.messages.length) {
    host.replaceChildren();
    renderedChatCount = 0;
  }
  for (const message of state.chat.messages.slice(renderedChatCount)) {
    host.appendChild(chatMessageNode(message));
  }
  renderedChatCount = state.chat.messages.length;
  renderedChatSignature = signature;
  host.scrollTop = host.scrollHeight;
}

function chatEmptyNode(text) {
  const node = document.createElement("p");
  node.className = "chat-empty";
  node.textContent = text;
  return node;
}

function chatMessageNode(message) {
  const node = document.createElement("div");
  node.className = `chat-message ${escapeHtml(message.role)}`;
  const label = document.createElement("strong");
  label.textContent = message.role === "user" ? "You" : "AI";
  const body = document.createElement("p");
  body.textContent = message.content;
  node.append(label, body);
  return node;
}

function chatStageLabel() {
  if (state.userMode === "simple") {
    const labels = {
      upload: "Guided step 1: Upload",
      plan: "Guided step 2: Teeth and time",
      details: "Guided step 3: Details",
      review: "Guided step 4: Review",
      preview: "Guided step 5: 3D preview",
      print: "Guided step 6: Print / send",
    };
    return labels[state.guided.step] || "Guided workflow";
  }
  const labels = {
    upload: "Technician: Upload",
    availability: "Technician: Data",
    settings: "Technician: Settings",
    stages: "Technician: Stages",
    review: "Technician: Review",
    toothmap: "Reference: Tooth map",
    glossary: "Reference: Glossary",
    photos: "Reference: Imaging guide",
  };
  return labels[state.activeStep] || "Technician workflow";
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

let evaluateTimer = null;
// Monotonic token so a slow in-flight request can never overwrite a newer one.
const evalLatest = createLatest();

function scheduleEvaluate() {
  if (evaluateTimer) clearTimeout(evaluateTimer);
  evaluateTimer = setTimeout(runEvaluate, 150);
}

async function runEvaluate() {
  const token = evalLatest.next();
  try {
    const result = await evaluatePlan(planJson());
    if (!evalLatest.isCurrent(token)) return; // a newer evaluation superseded this one
    state.engineError = null;
    if (result.ok === false) {
      state.lastEval = null;
      renderEngineErrors(result.errors || ["plan was rejected by the engine"]);
    } else {
      state.lastEval = result;
      renderEvaluation(result);
    }
  } catch (error) {
    if (!evalLatest.isCurrent(token)) return;
    state.lastEval = null;
    state.engineError = error.message;
    renderEngineOffline();
  }
}

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
  document.querySelectorAll("[data-journey-step]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.journeyStep === state.activeStep);
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
  let markup;
  if (state.files.length) {
    markup = `
      <div class="upload-file-heading">
        <strong>${state.files.length === 1 ? "Uploaded STL" : "Uploaded STLs"}</strong>
        <button data-clear-uploads="true" type="button">Clear All</button>
      </div>
      ${state.uploadStorageStatus ? `<p>${escapeHtml(state.uploadStorageStatus)}</p>` : ""}
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
    // The Sample Test Case loads its two STL scans as already-present records, so
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
    markup = "<p>No STL files are stored yet. Select upper, lower, or both arches.</p>";
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
  renderPrintExport(result.print_export);
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
  container.dataset.tier = info.tier;
  container.innerHTML = `
    <p class="review-tier-label"><strong>${escapeHtml(info.label)}</strong></p>
    <p class="review-tier-summary">${escapeHtml(info.summary)}</p>
    ${info.root_bone_aware
      ? ""
      : `<p class="review-tier-note">Root/bone-aware review is not available for this plan.</p>`}
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

const ANATOMY_GROUP_LABELS = {
  roots: "Root geometry",
  tooth_axes: "Tooth axis",
  alveolar_bone: "Alveolar bone",
};

function renderAnatomyReview(anatomy) {
  const panel = el("anatomyPanel");
  const list = el("anatomyReviewList");
  if (!panel || !list) return;
  const groups = ["roots", "tooth_axes", "alveolar_bone"];
  const total = anatomy ? groups.reduce((n, g) => n + (anatomy[g]?.length || 0), 0) : 0;
  if (!anatomy || total === 0) {
    panel.hidden = true;
    list.innerHTML = "";
    return;
  }
  panel.hidden = false;
  const sections = groups.map((group) => {
    const items = anatomy[group] || [];
    return items.map((item, index) => anatomyRowMarkup(group, index, item)).join("");
  }).join("");
  const trustNote = anatomy.has_trusted
    ? "At least one object is trusted (reviewed and in field)."
    : "No object is trusted yet - root/bone-aware checks stay unavailable (fail-closed).";
  list.innerHTML = `<p class="review-tier-note">${escapeHtml(trustNote)}</p>${sections}`;
}

function anatomyRowMarkup(group, index, item) {
  const label = ANATOMY_GROUP_LABELS[group] || group;
  const tooth = item.tooth?.value ? ` ${item.tooth.value}` : "";
  const conf = item.confidence != null ? ` · conf ${Number(item.confidence).toFixed(2)}` : "";
  const flags = [
    item.trusted ? "trusted" : "not trusted",
    item.out_of_field ? "out of field" : null,
  ].filter(Boolean).join(" · ");
  const btn = (status, text) => `<button data-anatomy-review="${status}" data-anatomy-group="${group}" data-anatomy-index="${index}" type="button">${text}</button>`;
  return `
    <div class="segment-row anatomy-row" data-status="${escapeHtml(item.review_status)}">
      <span><strong>${escapeHtml(label)}${escapeHtml(tooth)}</strong> · ${escapeHtml(item.review_status)}${escapeHtml(conf)}</span>
      <small>${escapeHtml(flags)}</small>
      <span class="anatomy-actions">${btn("accepted", "Accept")}${btn("corrected", "Correct")}${btn("rejected", "Reject")}</span>
    </div>`;
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

function renderSegmentation() {
  const seg = state.segmentation;
  const status = el("segmentStatus");
  if (!status) return; // segment panel not present (e.g. trimmed markup)
  status.textContent = seg.busy ? "Working..." : "";
  el("proposeSegment").disabled = seg.busy;

  const proposal = seg.proposal;
  el("segmentFindings").innerHTML = proposal?.advisory_findings?.length
    ? proposal.advisory_findings
        .map((f) => `<li>${escapeHtml(f.title)}: ${escapeHtml(f.message)}</li>`)
        .join("")
    : "";

  const reanchor = el("reanchorSegment");
  const list = el("segmentList");
  if (!proposal?.teeth?.length) {
    list.innerHTML = seg.status ? `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` : "";
    el("applySegment").hidden = true;
    el("segmentApplied").textContent = "";
    if (reanchor) reanchor.hidden = true;
    return;
  }
  if (reanchor) {
    reanchor.hidden = false;
    reanchor.disabled = seg.busy;
  }
  const markedGapCount = parseMissingTeeth(seg.missingTeeth).length;
  list.innerHTML =
    `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` +
    countNoteMarkup(proposal.teeth, markedGapCount) +
    proposal.teeth.map(segmentRowMarkup).join("");
  el("applySegment").hidden = false;
  el("segmentApplied").textContent = seg.applied
    ? `Applied: ${seg.applied.tooth_meshes.length} tooth mesh(es) merged into the plan (draft).`
    : "Not applied yet.";
}

function segmentRowMarkup(tooth) {
  const edit = state.segmentation.edits[tooth.mesh_asset_id] || { tooth: tooth.tooth, included: true };
  const pct = Math.round((tooth.confidence || 0) * 100);
  const tier = confidenceTier(pct);
  const review = tier === "low" ? "Review" : "";
  return `
    <div class="segment-row">
      <input type="checkbox" data-segment-include="${escapeHtml(tooth.mesh_asset_id)}" ${edit.included ? "checked" : ""} aria-label="Include this tooth" />
      <input class="segment-tooth" data-segment-tooth="${escapeHtml(tooth.mesh_asset_id)}" value="${escapeHtml(edit.tooth)}" maxlength="2" aria-label="FDI tooth number" />
      <span class="segment-arch">${escapeHtml(tooth.arch)}</span>
      <span class="segment-conf" data-tier="${tier}"><span class="segment-conf-bar" style="width:${pct}%"></span></span>
      <span class="segment-conf-num" data-tier="${tier}">${pct}%${review ? ` · ${review}` : ""}</span>
    </div>`;
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

function renderDownloadActions() {
  el("downloadEvaluation").disabled = !state.lastEval;
  el("downloadPrintMetadata").disabled = !state.lastEval?.print_export;
}

function renderPrintExport(status) {
  if (!status) {
    el("printExportStatus").innerHTML = "";
    return;
  }
  const blockers = status.blockers?.length
    ? `<ul>${status.blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "<p>Print package inputs are complete for export.</p>";
  const artifacts = status.artifacts?.length
    ? `<p>${escapeHtml(status.artifacts.map((item) => item.filename).join(", "))}</p>`
    : "";
  el("printExportStatus").innerHTML = `
    <p><strong>${status.ready ? "Inputs complete" : "Inputs incomplete"}</strong></p>
    ${blockers}
    ${printReadiness(status.manufacturing_readiness)}
    ${printShellQa(status.shell_qa_findings)}
    ${printTolerances(status.printer_tolerances)}
    ${artifacts}
    <p>${escapeHtml(status.model_material)}</p>
    <p>${escapeHtml(status.thermoforming_material)}</p>
    <p>${escapeHtml(status.caveat)}</p>
  `;
}

function printVerdictClass(verdict) {
  if (verdict === "CONSISTENT") return "qa-ok";
  if (verdict === "ISSUES") return "qa-issue";
  return "qa-na";
}

function printReadiness(readiness) {
  if (!readiness?.verdict) return "";
  const reason = readiness.reason ? ` — ${escapeHtml(readiness.reason)}` : "";
  return `<p class="print-qa-readiness ${printVerdictClass(readiness.verdict)}">`
    + `<strong>Manufacturing readiness: ${escapeHtml(readiness.verdict)}</strong>${reason}</p>`;
}

function printShellQa(findings) {
  if (!Array.isArray(findings) || findings.length === 0) return "";
  const items = findings
    .map((finding) => `<li class="${printVerdictClass(finding.verdict)}">`
      + `${escapeHtml(finding.verdict)}: ${escapeHtml(finding.message)}</li>`)
    .join("");
  return `<ul class="print-qa-findings">${items}</ul>`;
}

function printTolerances(tolerances) {
  if (!tolerances) return "";
  const fmt = (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "—");
  return `<p class="print-qa-tolerances">Printer compensation: `
    + `XY ${fmt(tolerances.xy_compensation_mm)} mm, Z ${fmt(tolerances.z_compensation_mm)} mm · `
    + `min feature ${fmt(tolerances.minimum_printable_feature_mm)} mm.</p>`;
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
