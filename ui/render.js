import {
  availabilityLabels,
  cumulativeRows,
  dataGaps,
  el,
  findings,
  maxStage,
  numberValue,
  stages,
  state,
  toothPositions,
} from "./state.js";
import { planJson } from "./plan.js";

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
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
  renderSteps();
  renderMetadata();
  renderRows();
  renderFindings();
  renderTimeline();
  el("planJson").value = JSON.stringify(planJson(), null, 2);
  drawCanvas();
}

export function renderAvailability() {
  el("availabilityGrid").innerHTML = Object.entries(availabilityLabels).map(([key, label]) => `
    <label class="toggle">
      <span>${label}</span>
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

function renderFindings() {
  el("dataGapList").innerHTML = dataGaps().map((gap) => `<li>${escapeHtml(gap)}</li>`).join("");
  const items = findings();
  el("findingList").innerHTML = items.length
    ? items.map((finding) => `<li class="warning">${escapeHtml(finding)}</li>`).join("")
    : "<li>No deterministic findings</li>";
}

function renderTimeline() {
  const stageCount = stages().length;
  const days = stageCount * numberValue("wearInterval");
  el("timelineText").textContent = `${stageCount} stage(s), ${days} projected day(s). Projection excludes refinements, compliance variation, clinical pauses, and clinician-directed changes.`;
  const slider = el("stageSlider");
  slider.max = String(maxStage());
  if (Number(slider.value) > maxStage()) slider.value = String(maxStage());
  el("stageValue").textContent = slider.value;
}

function drawCanvas() {
  const canvas = el("archCanvas");
  const ctx = canvas.getContext("2d");
  const totals = cumulativeRows(Number(el("stageSlider").value || 0));
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
