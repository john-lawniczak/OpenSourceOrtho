import {
  availabilityLabels,
  el,
  evaluatePlan,
  iprContactPairs,
  numberValue,
  state,
  toothPositions,
} from "./state.js";
import { createLatest, escapeHtml, framePoseTotals, toothKind } from "./core.js";
import { createViewer } from "./viewer3d.js";
import { planJson } from "./plan.js";
import { renderGuided } from "./guided.js";

let viewer = null;
let viewerFailed = false;
// One-shot request to re-frame the camera once the next evaluation has populated
// the scene. Used when a new scene becomes visible (sample screen, guided 3D
// step) where the viewer may have been sized while hidden or framed for a
// different scene. It is honored after the async evaluation renders, so the fit
// uses the real container size and the new geometry.
let pendingRefit = false;

export function requestViewerRefit() {
  pendingRefit = true;
}

function ensureViewer() {
  if (viewer || viewerFailed) return viewer;
  try {
    viewer = createViewer(el("viewer3d"));
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
    ? state.files.map((file) => ({ name: file.name, file, arch: inferSourceArch(file.name) }))
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
  const renderMeshes = result.render_meshes?.length
    ? result.render_meshes
    : (state.useDemoMeshes ? demoRenderMeshes() : []);
  const filteredRenderMeshes = renderMeshes.filter((item) => toothMatchesArch(item.tooth));
  if (filteredRenderMeshes.length) {
    v.loadMeshes(filteredRenderMeshes).then((loaded) => {
      if (loaded && state.lastEval === result) updateViewer(result);
    });
  }
  const visibleResult = filterResultForArch(result);
  v.update({
    frames: visibleResult.frames,
    toothFrames: visibleResult.tooth_frames,
    attachments: visibleResult.clinical_controls?.attachments || [],
    initialOffsets: state.demoInitialOffsets,
    stageIndex: Number(el("stageSlider").value || 0),
    view: state.view,
    exaggeration: numberValue("exaggeration") || 1,
    showToothLabels: state.showToothLabels,
  });
}

export function renderAll() {
  document.body.dataset.mode = state.userMode;
  document.body.dataset.theme = state.theme;
  document.body.dataset.step = state.activeStep;
  document.body.dataset.sample = state.sample.active ? "1" : "";
  document.body.dataset.generationDetail = state.detailMode.generation;
  document.body.dataset.aiDetail = state.detailMode.ai;
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
  state.chat.provider = el("chatProvider").value;
  state.chat.model = el("chatModel").value;
  state.chat.contextScope = el("chatScope").value;
  state.chat.input = el("chatInput").value;
  state.chat.apiKeyPresent = Boolean(el("chatApiKey").value.trim());
  state.chat.agentAccessEnabled = el("agentAccessEnabled").checked;
  state.chat.agentEndpoint = el("agentEndpoint").value;
  state.generation.acknowledged = el("generationAck").checked;
  state.generation.notes = el("generationNotes").value;
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
  renderRows();
  renderIprContactMap();
  renderChat();
  renderGeneration();
  renderDetailModes();
  renderVersions();
  renderScanStatus();
  renderSampleStatus();
  renderSegmentation();
  renderDownloadActions();
  el("planJson").value = JSON.stringify(planJson(), null, 2);
  el("stageValue").textContent = el("stageSlider").value;
  scheduleEvaluate();
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
}

function renderReviewHeading() {
  el("reviewHeading").textContent = state.activeStep === "sample" ? "Sample Test Case" : "Progress Preview";
}

function filterScanSources(sources) {
  if (state.scanArchFilter === "both") return sources;
  return sources.filter((source) => (source.arch || inferSourceArch(source.name)) === state.scanArchFilter);
}

function inferSourceArch(name = "") {
  const text = name.toLowerCase();
  if (
    text.includes("upper") ||
    text.includes("top") ||
    text.includes("maxilla") ||
    text.includes("maxillary") ||
    /(^|[-_\s])u(\.stl|[-_\s])/.test(text)
  ) {
    return "maxillary";
  }
  if (
    text.includes("lower") ||
    text.includes("bottom") ||
    text.includes("mandible") ||
    text.includes("mandibular") ||
    /(^|[-_\s])l(\.stl|[-_\s])/.test(text)
  ) {
    return "mandibular";
  }
  return null;
}

function toothMatchesArch(tooth) {
  if (state.scanArchFilter === "both") return true;
  const q = String(tooth || "")[0];
  let arch = null;
  if (q === "1" || q === "2") arch = "maxillary";
  if (q === "3" || q === "4") arch = "mandibular";
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
  mcp: "Paste the API key your MCP host expects (set the endpoint under Advanced). Used only for this session.",
  odysseus: "Paste your Odysseus API key. It is used only for this session and never saved.",
  "open-source": "Paste the API key for your model endpoint (set it under Advanced). Used only for this session.",
};

export function renderChat() {
  el("chatProvider").value = state.chat.provider;
  el("chatModel").value = state.chat.model;
  el("chatScope").value = state.chat.contextScope;
  el("chatInput").value = state.chat.input;
  el("agentAccessEnabled").checked = state.chat.agentAccessEnabled;
  el("agentEndpoint").value = state.chat.agentEndpoint;
  el("sendChat").disabled = state.chat.busy || !state.chat.input.trim();
  // The local helper needs no key, so hide the key field for it; for any real
  // provider show the field with provider-specific, plain-language instructions.
  const isLocal = state.chat.provider === "local";
  el("aiKeyField").hidden = isLocal;
  el("aiKeyHelp").textContent = AI_KEY_HELP[state.chat.provider] || AI_KEY_HELP.local;
  const secretStatus = state.chat.apiKeyPresent ? " · key in session" : "";
  const agentStatus = state.chat.agentAccessEnabled ? " · agent access staged" : "";
  el("chatStatus").textContent = `${state.chat.status}${secretStatus}${agentStatus}`;
  el("chatMessages").innerHTML = state.chat.messages.length
    ? state.chat.messages.map((message) => `
      <div class="chat-message ${escapeHtml(message.role)}">
        <strong>${message.role === "user" ? "You" : "AI"}</strong>
        <p>${escapeHtml(message.content)}</p>
      </div>
    `).join("")
    : "<p class=\"chat-empty\">Ask what the preview can and cannot tell you.</p>";
}

export function renderGeneration() {
  const gen = state.generation;
  el("generationAck").checked = gen.acknowledged;
  el("generationNotes").value = gen.notes;
  el("generatePlan").disabled = gen.busy;
  el("generationStatus").textContent = gen.busy ? "Working..." : (gen.status || "Ready");
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
            <small>${Math.round(file.size / 1024)} KB</small>
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
  ] : sources.length ? [
    ["Files", sources.map((source) => source.name).join(", ")],
    ["Size", "repo example"],
    ["Units", state.scanUnits],
    ["Arch", "upper + lower"],
  ] : [["Files", "none"], ["Size", "0 KB"], ["Units", state.scanUnits], ["Arch", "unknown"]];
  el("scanMetadata").innerHTML = items
    .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("");
}

function renderEvaluation(result) {
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
  el("stageValue").textContent = slider.value;
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
  renderDownloadActions();
}

function renderScanStatus() {
  el("scanRenderStatus").textContent = state.scanRenderStatus;
  el("scanArchFilter").value = state.scanArchFilter;
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

  const list = el("segmentList");
  if (!proposal?.teeth?.length) {
    list.innerHTML = seg.status ? `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` : "";
    el("applySegment").hidden = true;
    el("segmentApplied").textContent = "";
    return;
  }
  list.innerHTML =
    `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` +
    proposal.teeth.map(segmentRowMarkup).join("");
  el("applySegment").hidden = false;
  el("segmentApplied").textContent = seg.applied
    ? `Applied: ${seg.applied.tooth_meshes.length} tooth mesh(es) merged into the plan (draft).`
    : "Not applied yet.";
}

function segmentRowMarkup(tooth) {
  const edit = state.segmentation.edits[tooth.mesh_asset_id] || { tooth: tooth.tooth, included: true };
  const pct = Math.round((tooth.confidence || 0) * 100);
  return `
    <div class="segment-row">
      <input type="checkbox" data-segment-include="${escapeHtml(tooth.mesh_asset_id)}" ${edit.included ? "checked" : ""} aria-label="Include this tooth" />
      <input class="segment-tooth" data-segment-tooth="${escapeHtml(tooth.mesh_asset_id)}" value="${escapeHtml(edit.tooth)}" maxlength="2" aria-label="FDI tooth number" />
      <span class="segment-arch">${escapeHtml(tooth.arch)}</span>
      <span class="segment-conf"><span class="segment-conf-bar" style="width:${pct}%"></span></span>
      <span class="segment-conf-num">${pct}%</span>
    </div>`;
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
    : "<p>Print package inputs are ready for export.</p>";
  const artifacts = status.artifacts?.length
    ? `<p>${escapeHtml(status.artifacts.map((item) => item.filename).join(", "))}</p>`
    : "";
  el("printExportStatus").innerHTML = `
    <p><strong>${status.ready ? "Ready" : "Not ready"}</strong></p>
    ${blockers}
    ${artifacts}
    <p>${escapeHtml(status.model_material)}</p>
    <p>${escapeHtml(status.thermoforming_material)}</p>
    <p>${escapeHtml(status.caveat)}</p>
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
