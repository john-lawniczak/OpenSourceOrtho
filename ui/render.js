import {
  availabilityLabels,
  el,
  evaluatePlan,
  numberValue,
  state,
  toothPositions,
} from "./state.js";
import { createLatest, escapeHtml, framePoseTotals } from "./core.js";
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
  renderAll();
}

function updateViewer(result) {
  if (state.dim !== "3d") return;
  const v = ensureViewer();
  if (!v) return;
  v.resize();
  v.update({
    frames: result.frames,
    toothFrames: result.tooth_frames,
    stageIndex: Number(el("stageSlider").value || 0),
    view: state.view,
    exaggeration: numberValue("exaggeration") || 1,
  });
}

export function renderAll() {
  state.scanUnits = el("scanUnits").value;
  state.scanArch = el("scanArch").value;
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
  renderSteps();
  renderMetadata();
  renderRows();
  el("planJson").value = JSON.stringify(planJson(), null, 2);
  el("stageValue").textContent = el("stageSlider").value;
  scheduleEvaluate();
  drawCanvas();
  if (state.lastEval) updateViewer(state.lastEval);
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
  document.querySelectorAll(".step").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.step === state.activeStep);
  });
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("is-active"));
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
  const items = state.file ? [
    ["File", state.file.name],
    ["Size", `${Math.round(state.file.size / 1024)} KB`],
    ["Units", state.scanUnits],
    ["Arch", state.scanArch || "unknown"],
  ] : [["File", "none"], ["Size", "0 KB"], ["Units", state.scanUnits], ["Arch", "unknown"]];
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
  el("timelineText").textContent = "Engine offline - no projection available.";
}

function renderPrintExport(status) {
  if (!status) {
    el("printExportStatus").innerHTML = "";
    return;
  }
  const blockers = status.blockers?.length
    ? `<ul>${status.blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "<p>Export metadata is ready for handoff review.</p>";
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

function drawCanvas() {
  const canvas = el("archCanvas");
  const ctx = canvas.getContext("2d");
  const stageIndex = Number(el("stageSlider").value || 0);
  const totals = framePoseTotals(state.lastEval?.frames?.[stageIndex]);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#fbfdfe";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#cdd6dc";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(520, 258, 410, 210, 0, 0, Math.PI * 2);
  ctx.stroke();

  for (const [tooth, [x, y]] of Object.entries(toothPositions)) {
    const movement = totals.get(tooth) || { x: 0, y: 0, z: 0 };
    const dx = movement.x * 80;
    const dy = movement.y * 80 - movement.z * 35;
    if (state.view === "overlay" || state.view === "current") drawTooth(ctx, x, y, tooth, "#dfe8ed", "#60707a");
    if (state.view === "overlay" || state.view === "planned") {
      drawTooth(ctx, x + dx, y + dy, tooth, "#0f766e", "#ffffff");
      if (Math.hypot(dx, dy) > 1) {
        ctx.strokeStyle = "#2563eb";
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + dx, y + dy);
        ctx.stroke();
      }
    }
  }
}

function drawTooth(ctx, x, y, label, fill, text) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = "#6f828b";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  roundedRect(ctx, x - 18, y - 14, 36, 28, 7);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = text;
  ctx.font = "12px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, x, y);
}

function roundedRect(ctx, x, y, width, height, radius) {
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
}
