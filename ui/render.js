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

let viewer = null;
let viewerFailed = false;

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
  const scanSources = state.files.length
    ? state.files.map((file) => ({ name: file.name, file }))
    : state.scanSources;
  if (scanSources.length) {
    v.loadScanSources(scanSources).then(({ loaded, count }) => {
      const sourceType = state.files.length ? "uploaded" : "canonical example";
      state.scanRenderStatus = count
        ? `Rendering exact ${sourceType} scan mesh${count === 1 ? "" : "es"} (${scanSources.map((source) => source.name).join(", ")}). Staged movement remains simulated unless segmented per-tooth meshes are provided.`
        : "No uploaded STL scan mesh could be rendered.";
      renderScanStatus();
      if (loaded && state.lastEval === result) updateViewer(result);
    }).catch((error) => {
      state.scanRenderStatus = `Uploaded STL render failed: ${error.message}`;
      renderScanStatus();
    });
  } else {
    v.loadScanSources([]);
    state.scanRenderStatus = state.useDemoMeshes
      ? "Rendering bundled demo tooth meshes."
      : "No uploaded scan mesh is loaded; review uses schematic proxy teeth.";
    renderScanStatus();
  }
  const renderMeshes = result.render_meshes?.length
    ? result.render_meshes
    : (state.useDemoMeshes ? demoRenderMeshes() : []);
  if (renderMeshes.length) {
    v.loadMeshes(renderMeshes).then((loaded) => {
      if (loaded && state.lastEval === result) updateViewer(result);
    });
  }
  v.update({
    frames: result.frames,
    toothFrames: result.tooth_frames,
    attachments: result.clinical_controls?.attachments || [],
    initialOffsets: state.demoInitialOffsets,
    stageIndex: Number(el("stageSlider").value || 0),
    view: state.view,
    exaggeration: numberValue("exaggeration") || 1,
  });
}

export function renderAll() {
  document.body.dataset.mode = state.userMode;
  document.body.dataset.theme = state.theme;
  el("themeToggle").textContent = state.theme === "dark" ? "Light Mode" : "Dark Mode";
  state.scanUnits = el("scanUnits").value;
  state.scanArch = el("scanArch").value;
  state.simpleGoal = el("simpleGoal").value;
  state.simpleAcknowledged = el("simpleAcknowledged").checked;
  el("simpleReview").disabled = !state.simpleAcknowledged;
  state.chat.provider = el("chatProvider").value;
  state.chat.model = el("chatModel").value;
  state.chat.contextScope = el("chatScope").value;
  state.chat.input = el("chatInput").value;
  state.chat.apiKeyPresent = Boolean(el("chatApiKey").value.trim());
  state.chat.agentAccessEnabled = el("agentAccessEnabled").checked;
  state.chat.agentEndpoint = el("agentEndpoint").value;
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
  renderMetadata();
  renderRows();
  renderIprContactMap();
  renderChat();
  renderScanStatus();
  renderDownloadActions();
  el("planJson").value = JSON.stringify(planJson(), null, 2);
  el("stageValue").textContent = el("stageSlider").value;
  scheduleEvaluate();
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
}

export function renderChat() {
  el("chatProvider").value = state.chat.provider;
  el("chatModel").value = state.chat.model;
  el("chatScope").value = state.chat.contextScope;
  el("chatInput").value = state.chat.input;
  el("agentAccessEnabled").checked = state.chat.agentAccessEnabled;
  el("agentEndpoint").value = state.chat.agentEndpoint;
  el("sendChat").disabled = state.chat.busy || !state.chat.input.trim();
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
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("is-active"));
  if (state.userMode === "simple" && state.activeStep !== "review") {
    el("panel-simple").classList.add("is-active");
    return;
  }
  el(`panel-${state.activeStep}`).classList.add("is-active");
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
  const totals = framePoseTotals(state.lastEval?.frames?.[stageIndex]);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = canvasColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(520, 258, 410, 210, 0, 0, Math.PI * 2);
  ctx.stroke();

  for (const [tooth, [x, y]] of Object.entries(toothPositions)) {
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
